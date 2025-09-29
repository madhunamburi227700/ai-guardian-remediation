import os
import logging

from ai_guardian_remediation.core.agents.sast_remediation import (
    DEFAULT_CLONE_TMP_DIRECTORY,
    DEFAULT_REMEDIATION_SUB_DIR,
)
from ai_guardian_remediation.config import settings

from ai_guardian_remediation.core.agents.sast_remediation.factory import get_sast_agent
from ai_guardian_remediation.common.git_manager import GitRepoManager
from ai_guardian_remediation.common.utils import (
    format_message,
    prepare_message,
    get_clone_directory_name,
    create_branch_name_for_sast_remediation,
    generate_repo_url,
)
from ai_guardian_remediation.common.scm_providers.base import get_git_provider


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
        scan_result_id: str,
    ):
        # TODO: Verify that this url is github and is able to get the root url
        # TODO: Some initial checks
        self.git_remote_url = generate_repo_url(platform, organization, repository)
        self.branch = branch
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(
            branch, rule, file_path, line_no, scan_result_id
        )
        self.file_path = file_path
        self.rule = rule
        self.rule_message = rule_message
        self.line_no = line_no
        self.scan_result_id = scan_result_id
        self.provider = platform.lower()
        # self.db_session = session

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
            rule_message=rule_message,
            scm_secret=self.git_token,
        )

    def _get_cloned_path(self, branch, rule, file_path, line_no, scan_result_id):
        clone_dir = get_clone_directory_name(
            self.git_remote_url, branch, rule, file_path, str(line_no), scan_result_id
        )
        return os.path.join(
            DEFAULT_CLONE_TMP_DIRECTORY, DEFAULT_REMEDIATION_SUB_DIR, clone_dir
        )

    async def generate_fix(self):
        try:
            yield format_message(
                prepare_message(
                    "debug", f"The repo {self.git_remote_url} is about to be cloned"
                )
            )

            is_cloned = self.git_manager.clone_repo()
            if not is_cloned:
                raise Exception(
                    "The repository could not be cloned, check repository URL or access rights"
                )

            yield format_message(
                prepare_message(
                    "debug", f"The repo {self.git_remote_url} has been cloned"
                )
            )

            async for data in self.agent.generate_fix():
                yield format_message(data)

            diff: str = self.git_manager.calculate_branch_diff(
                self.git_manager.get_current_branch()
            )
            if diff:
                yield format_message(prepare_message("diff", diff))

        except Exception as e:
            logging.error(f"Error in streaming: {str(e)}")
            yield format_message(prepare_message("error", str(e)))
        finally:
            yield format_message(prepare_message("done"))

    async def process_approval(self):
        try:
            yield format_message(
                prepare_message("debug", "Starting the process of creating a PR")
            )
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
                base_branch=self.branch,
                to_branch=fix_branch,
                title=f"fix: semgrep-{self.rule}",
                body=pr_template.format(
                    file_path=self.file_path,
                    rule=self.rule,
                    rule_message=self.rule_message,
                    line_no=self.line_no,
                ),
            )
            yield format_message(
                prepare_message("debug", f"PR {pr_link} has been created.")
            )
        except Exception as e:
            yield format_message(prepare_message("error", str(e)))
        finally:
            yield format_message(prepare_message("done"))
            if self.git_manager:
                self.git_manager.cleanup_repo()

    def cleanup(self):
        if self.git_manager:
            self.git_manager.cleanup_repo()
