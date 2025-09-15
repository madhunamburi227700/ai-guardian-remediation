import os

from ai_guardian_remediation.core.agents.cve_remediation import (
    DEFAULT_CLONE_TMP_DIRECTORY,
    DEFAULT_REMEDIATION_SUB_DIR,
)
from ai_guardian_remediation.config import settings

from ai_guardian_remediation.core.agents.cve_remediation.factory import get_cve_agent
from ai_guardian_remediation.common.git_manager import GitRepoManager


from ai_guardian_remediation.common.utils import (
    format_stream_data,
    get_clone_directory_name,
    sanitize_github_url,
)


class CVERemediationService:
    def __init__(
        self,
        cve_id: str,
        package: str,
        git_token: str,
        remote_url: str,
        branch: str,
        user_email,
    ):
        # TODO: Change this for other SCMs
        self.git_remote_url = sanitize_github_url(remote_url)
        self.cve_id = cve_id
        self.package = package

        # Change this
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(user_email, branch, cve_id)
        self.git_manager = GitRepoManager(
            repo_url=remote_url,
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

    def _get_cloned_path(self, user_email, branch, cve_id):
        clone_dir = get_clone_directory_name(
            self.git_remote_url, branch, cve_id, user_email
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

        except Exception as e:
            print(f"Error in streaming: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield format_stream_data(error_data)
        finally:
            # Send completion marker
            print("Sending completion marker")
            yield format_stream_data({"type": "done"})

    async def apply_fix(
        self, session_id: str = None, message_type: str = None, user_message=None
    ):
        try:
            # Run the agent
            async for data in self.agent.apply_fix(
                session_id, self.cve_id, self.package, message_type, user_message
            ):
                yield format_stream_data(data)

            yield format_stream_data(data)

        except Exception as e:
            print(f"Error in streaming: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield format_stream_data(error_data)
        finally:
            # Send completion marker
            print("Sending completion marker")
            yield format_stream_data({"type": "done"})
            # repo cleanup
            if self.git_manager:
                self.git_manager.cleanup_repo()
