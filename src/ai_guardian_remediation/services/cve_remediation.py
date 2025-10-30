import os

from ai_guardian_remediation.common.db_manager import DatabaseManager
from ai_guardian_remediation.common.event_streamer import EventStreamer
from ai_guardian_remediation.common.scm_providers.base import get_git_provider
from ai_guardian_remediation.core.agents.cve_remediation import (
    DEFAULT_CLONE_TMP_DIRECTORY,
    DEFAULT_REMEDIATION_SUB_DIR,
)
from ai_guardian_remediation.config import settings

from ai_guardian_remediation.core.agents.cve_remediation.factory import get_cve_agent
from ai_guardian_remediation.common.git_manager import GitRepoManager

from ai_guardian_remediation.common.utils import (
    detect_provider,
    get_clone_directory_name,
    generate_repo_url,
    create_branch_name_for_cve_remediation,
)

import logging

from ai_guardian_remediation.storage.db.db import Session
from ai_guardian_remediation.storage.db.remediation import Status


pr_template = """### Pull Request — CVE Fix

- CVE ID: {cve_id}
- Package: {package}
"""


class CVERemediationService:
    def __init__(
        self,
        cve_id: str,
        package: str,
        git_token: str,
        platform: str,
        organization: str,
        repository: str,
        branch: str,
        vulnerability_id: str,
        remediation_id: str = None,
    ):
        # TODO: Change this for other SCMs
        self.git_remote_url = generate_repo_url(platform, organization, repository)
        self.cve_id = cve_id
        self.package = package
        self.vulnerability_id = vulnerability_id
        self.remediation_id = remediation_id

        # Change this
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(
            vulnerability_id,
            repository,
            branch,
            cve_id,
        )
        self.provider = detect_provider(self.git_remote_url)
        self.db_manager = DatabaseManager(Session())

        self.git_manager = GitRepoManager(
            repo_url=self.git_remote_url,
            branch=branch,
            clone_path=self.clone_path,
            token=git_token,
        )
        self.branch = self.git_manager.branch
        self.agent = get_cve_agent(
            provider=settings.REMEDIATION_AGENT,
            clone_path=self.clone_path,
            repo_url=self.git_remote_url,
            branch=self.branch,
            scm_secret=self.git_token,
        )

    def _get_cloned_path(self, vulnerability_id, repository, branch, cve_id):
        clone_dir = get_clone_directory_name(
            self.git_remote_url,
            vulnerability_id,
            repository,
            branch,
            cve_id,
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
                        "The repository could not be cloned, try checking whether the token entered has the right permissions"
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

            if not os.path.exists(self.clone_path):
                raise Exception(
                    f"The cloned directory could not be found for repository {self.git_remote_url}"
                )

            async for data in self.agent.solutionize(
                session_id, self.cve_id, self.package, message_type, user_message
            ):
                yield streamer.emit(raw_data=data)

            diff: str = self.git_manager.calculate_branch_diff(self.branch)

            if diff != "":
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
            # Send completion marker
            logging.info("Sending completion marker")
            yield streamer.emit("done")
            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                None,
                {"conversation": streamer.all()},
            )

    async def apply_fix(self):
        streamer = EventStreamer()
        try:
            yield streamer.emit("debug", "Starting the process of creating a PR")

            fix_branch = create_branch_name_for_cve_remediation(
                self.cve_id, self.package
            )
            self.git_manager.commit_to_branch(
                fix_branch, f"fix: {self.cve_id}-{self.package}"
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
                title=f"fix: cve-{self.cve_id}-{self.package}",
                body=pr_template.format(cve_id=self.cve_id, package=self.package),
            )

            yield streamer.emit("debug", f"PR {pr_link} has been created.")

            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                Status.PR_RAISED,
                {"pr_link": pr_link, "fix_branch": fix_branch},
            )
        except Exception as e:
            yield streamer.emit("error", str(e))
        finally:
            yield streamer.emit("done")
            if self.git_manager:
                self.git_manager.cleanup_repo()

            await self.db_manager.save_remediation(
                self.remediation_id,
                self.vulnerability_id,
                None,
                {"conversation": streamer.all()},
            )
