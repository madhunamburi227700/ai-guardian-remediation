import os
import logging
from typing import Optional

from ai_guardian_remediation.common.db_manager import (
    DatabaseManager,
    NoOpDatabaseManager,
)
from ai_guardian_remediation.common.email_manager import EmailManager
from ai_guardian_remediation.common.event_streamer import EventStreamer
from ai_guardian_remediation.core.agents.sast_remediation import (
    DEFAULT_CLONE_TMP_DIRECTORY,
    DEFAULT_REMEDIATION_SUB_DIR,
)
from ai_guardian_remediation.config import settings

from ai_guardian_remediation.core.agents.sast_remediation.factory import get_sast_agent
from ai_guardian_remediation.common.git_manager import GitRepoManager
from ai_guardian_remediation.common.utils import (
    get_clone_directory_name,
    create_branch_name_for_sast_remediation,
    generate_repo_url,
)
from ai_guardian_remediation.common.scm_providers.base import get_git_provider
from ai_guardian_remediation.storage.db.db import Session
from ai_guardian_remediation.storage.db.remediation import Status


pr_template = """### Pull Request — Semgrep Rule Fix

- Rule ID: {rule}
- Rule Message: {rule_message}
- File Path: {file_path}
- Line: {line_no}
"""


class SASTRemediationService:
    def __init__(
        self,
        platform: str,
        organization: str,
        repository: str,
        branch: str,
        rule: str,
        rule_message: str,
        file_path: str,
        line_no: int,
        git_token: str,  # token for GitRepoManager
        vulnerability_id: str,
        remediation_id: str = None,
        user_email: Optional[str] = None,
    ):
        # TODO: Verify that this url is github and is able to get the root url
        # TODO: Some initial checks
        self.git_remote_url = generate_repo_url(platform, organization, repository)
        self.branch = branch
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(
            branch, rule, file_path, line_no, vulnerability_id, remediation_id
        )
        self.file_path = file_path
        self.rule = rule
        self.rule_message = rule_message
        self.line_no = line_no
        self.remediation_id = remediation_id
        self.vulnerability_id = vulnerability_id
        self.provider = platform.lower()
        self.db_manager = (
            DatabaseManager(Session()) if settings.DB_ENABLED else NoOpDatabaseManager()
        )
        self.email_manager = EmailManager(user_email, "SAST")

        # Git operations
        self.git_manager = GitRepoManager(
            repo_url=self.git_remote_url,
            branch=branch,
            clone_path=self.clone_path,
            token=git_token,  # token passed here
        )

        # Agent needs SCM secret for MCP/GitHub commands
        self.agent = get_sast_agent(
            provider=settings.REMEDIATION_AGENT,
            clone_path=self.clone_path,
            repo_url=self.git_remote_url,
            branch=branch,
            file_path=file_path,
            line_number=line_no,
            rule=rule,
            rule_message=rule_message,
            scm_secret=self.git_token,
        )

    def _get_cloned_path(
        self, branch, rule, file_path, line_no, vulnerability_id, remediation_id
    ):
        clone_dir = get_clone_directory_name(
            self.git_remote_url,
            branch,
            rule,
            file_path,
            str(line_no),
            vulnerability_id,
            remediation_id,
        )
        return os.path.join(
            DEFAULT_CLONE_TMP_DIRECTORY, DEFAULT_REMEDIATION_SUB_DIR, clone_dir
        )

    async def generate_fix(
        self, session_id: str = None, message_type: str = None, user_message=None
    ):
        streamer = EventStreamer()
        try:
            if message_type == "start_generate":
                yield streamer.emit(
                    "debug", f"The repo {self.git_remote_url} is about to be cloned"
                )

                is_cloned = self.git_manager.clone_repo()
                if not is_cloned:
                    raise Exception(
                        "The repository could not be cloned, check repository URL or access rights"
                    )

                yield streamer.emit(
                    "debug", f"The repo {self.git_remote_url} has been cloned"
                )

                await self.db_manager.save_remediation(
                    self.remediation_id,
                    self.vulnerability_id,
                    Status.STARTED,
                    {"pr_link": "", "fix_branch": "", "conversation": None},
                )

            if user_message and message_type == "followup":
                streamer.emit("user", user_message)

            if not os.path.exists(self.clone_path):
                raise Exception(
                    f"The cloned directory could not be found for repository {self.git_remote_url}"
                )

            async for data in self.agent.generate_fix(
                session_id, message_type, user_message
            ):
                yield streamer.emit(raw_data=data)

            diff: str = self.git_manager.calculate_branch_diff(
                self.git_manager.get_current_branch()
            )
            if diff:
                yield streamer.emit("diff", diff)

            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                Status.FIX_GENERATED if diff else Status.FIX_PENDING,
            )

        except Exception as e:
            logging.error(f"Error in streaming: {str(e)}")
            yield streamer.emit("error", str(e))
        finally:
            yield streamer.emit("done")
            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                None,
                {"conversation": streamer.all()},
            )

    async def process_approval(self):
        streamer = EventStreamer()
        try:
            yield streamer.emit("debug", "Starting the process of creating a PR")

            fix_branch = create_branch_name_for_sast_remediation(
                self.rule, self.line_no
            )
            self.git_manager.commit_to_branch(
                fix_branch, f"fix: {self.rule}-{self.line_no}"
            )

            scm_provider = get_git_provider(
                provider_type=self.provider,
                repo_url=self.git_remote_url,
                clone_path=self.clone_path,
                token=self.git_token,
            )

            pr_link = scm_provider.create_pull_request(
                target_branch=self.branch,
                source_branch=fix_branch,
                title=f"fix: semgrep-{self.rule}",
                body=pr_template.format(
                    file_path=self.file_path,
                    rule=self.rule,
                    rule_message=self.rule_message,
                    line_no=self.line_no,
                ),
            )
            yield streamer.emit("debug", f"PR {pr_link} has been created.")

            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                Status.PR_RAISED,
                {"pr_link": pr_link, "fix_branch": fix_branch},
            )

            self.email_manager.send_approval_notification(
                {
                    "repository": self.git_remote_url,
                    "branch": fix_branch,
                    "pr_url": pr_link,
                    "finding": self.rule,
                }
            )

            if self.git_manager:
                self.git_manager.cleanup_repo()

        except Exception as e:
            yield streamer.emit("error", str(e))
        finally:
            yield streamer.emit("done")
            # if self.git_manager:
            #     self.git_manager.cleanup_repo()
            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                None,
                {"conversation": streamer.all()},
            )

    async def cleanup(self):
        streamer = EventStreamer()
        if self.git_manager:
            self.git_manager.cleanup_repo()
            yield streamer.emit("debug", "Cleaned up the cloned repository")
        yield streamer.emit("done")
