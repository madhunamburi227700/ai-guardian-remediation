import os
from ai_guardian_remediation.core.agents.sast_remediation import (
    DEFAULT_CLONE_TMP_DIRECTORY,
    DEFAULT_REMEDIATION_SUB_DIR,
)
from ai_guardian_remediation.config import settings

from ai_guardian_remediation.core.agents.sast_remediation.factory import get_sast_agent
from ai_guardian_remediation.common.git_manager import GitRepoManager
from ai_guardian_remediation.common.utils import (
    format_stream_data,
    get_clone_directory_name,
)


class SASTRemediationService:
    def __init__(
        self,
        repository_url: str,
        branch: str,
        rule: str,
        rule_message: str,
        file_path: str,
        line_no: int,
        git_token: str,  # token for GitRepoManager
    ):
        # TODO: Verify that this url is github and is able to get the root url
        # TODO: Some initial checks
        self.git_remote_url = repository_url
        self.git_token = git_token
        self.clone_path = self._get_cloned_path(branch, rule, file_path, line_no)

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
            scm_secret=self.git_token,  # SCM token for GitHub operations
        )

    def _get_cloned_path(self, branch, rule, file_path, line_no):
        clone_dir = get_clone_directory_name(
            self.git_remote_url, branch, rule, file_path, str(line_no)
        )
        return os.path.join(
            DEFAULT_CLONE_TMP_DIRECTORY, DEFAULT_REMEDIATION_SUB_DIR, clone_dir
        )

    async def generate_fix(self):
        try:
            if not self.git_token:
                raise Exception("Github token is not set")

            yield format_stream_data(
                {
                    "type": "debug",
                    "data": f"The repo {self.git_remote_url} is about to be cloned",
                }
            )

            is_cloned = self.git_manager.clone_repo()
            if not is_cloned:
                raise Exception(
                    "The repository could not be cloned, check repository URL or access rights"
                )

            yield format_stream_data(
                {
                    "type": "debug",
                    "data": f"The repo {self.git_remote_url} has been cloned",
                }
            )

            async for data in self.agent.generate_fix():
                yield format_stream_data(data)

            diff: str = self.git_manager.calculate_branch_diff(
                self.git_manager.get_current_branch()
            )
            yield format_stream_data({"type": "diff", "content": diff})

        except Exception as e:
            yield format_stream_data({"type": "error", "error": str(e)})
        finally:
            yield format_stream_data({"type": "done"})

    async def process_approval(self):
        try:
            async for data in self.agent.process_approval():
                yield format_stream_data(data)
        except Exception as e:
            yield format_stream_data({"type": "error", "error": str(e)})
        finally:
            yield format_stream_data({"type": "done"})
            if self.git_manager:
                self.git_manager.cleanup_repo()

    def cleanup(self):
        if self.git_manager:
            self.git_manager.cleanup_repo()
