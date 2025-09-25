import os

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
    format_stream_data,
    get_clone_directory_name,
    generate_repo_url,
    create_branch_name_for_cve_remediation,
)

import logging

from ai_guardian_remediation.services.db import save_remediation
from ai_guardian_remediation.storage.db.db import session


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
        scan_result_id: str,
    ):
        # TODO: Change this for other SCMs
        self.git_remote_url = generate_repo_url(platform, organization, repository)
        self.cve_id = cve_id
        self.package = package
        self.scan_result_id = scan_result_id

        # Change this
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(scan_result_id, branch, cve_id)
        self.provider = detect_provider(self.git_remote_url)
        self.db_session = session

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

    def _get_cloned_path(self, scan_result_id, branch, cve_id):
        clone_dir = get_clone_directory_name(
            self.git_remote_url, branch, cve_id, scan_result_id
        )

        return os.path.join(
            DEFAULT_CLONE_TMP_DIRECTORY, DEFAULT_REMEDIATION_SUB_DIR, clone_dir
        )

    async def generate_fix(
        self, session_id: str = None, message_type: str = None, user_message=None
    ):
        try:
            if not self.git_token:
                raise Exception("Github token is not set")

            if message_type == "start_generate":
                data = {
                    "type": "debug",
                    "data": f"The repo {self.git_remote_url} is about to be cloned",
                }
                yield format_stream_data(data)
                is_cloned = self.git_manager.clone_repo()
                if not is_cloned:
                    raise Exception(
                        "The repository could not be cloned, try checking whether the token entered has the right permissions"
                    )

                data = {
                    "type": "debug",
                    "data": f"The repo {self.git_remote_url} has been cloned",
                }
                yield format_stream_data(data)

                await save_remediation(
                    self.db_session,
                    self.scan_result_id,
                    "started",
                    {"scan_result_id": self.scan_result_id, "pr_link": ""},
                )

            if not os.path.exists(self.clone_path):
                raise Exception(
                    f"The cloned directory could not be found for repository {self.git_remote_url}"
                )

            async for data in self.agent.solutionize(
                session_id, self.cve_id, self.package, message_type, user_message
            ):
                yield format_stream_data(data)

            diff: str = self.git_manager.calculate_branch_diff(self.branch)

            if diff != "":
                data = {
                    "type": "diff",
                    "content": diff,
                }
                yield format_stream_data(data)
                await save_remediation(
                    self.db_session, self.scan_result_id, "fix_generated"
                )

        except Exception as e:
            logging.error(f"Error in streaming: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield format_stream_data(error_data)
        finally:
            # Send completion marker
            logging.info("Sending completion marker")
            yield format_stream_data({"type": "done"})

    async def apply_fix(self):
        try:
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
                base_branch=self.branch,
                to_branch=fix_branch,
                title=f"fix: cve-{self.cve_id}-{self.package}",
                body=pr_template.format(cve_id=self.cve_id, package=self.package),
            )
            yield format_stream_data(
                {
                    "type": "debug",
                    "data": f"PR {pr_link} has been created.",
                }
            )

            await save_remediation(
                self.db_session, self.scan_result_id, "pr_raised", {"pr_link": pr_link}
            )
        except Exception as e:
            yield format_stream_data({"type": "error", "error": str(e)})
        finally:
            yield format_stream_data({"type": "done"})
            if self.git_manager:
                self.git_manager.cleanup_repo()
