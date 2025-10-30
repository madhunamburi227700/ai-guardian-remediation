from urllib.parse import urlparse
import logging
from github import Github

from ai_guardian_remediation.common.scm_providers.base import SCMProvider


class GithubProvider(SCMProvider):
    def __init__(self, repo_url, clone_path, token=None):
        self.repo_url = repo_url
        self.clone_path = clone_path
        self.token = token

    @staticmethod
    def extract_owner_repo(url):
        parsed = urlparse(url)
        path = parsed.path
        if path.endswith(".git"):
            path = path[:-4]
        return path.strip("/")

    def create_pull_request(self, target_branch, source_branch, title, body) -> str:
        try:
            gh_token = Github(self.token)
            owner_repo = GithubProvider.extract_owner_repo(self.repo_url)
            gh_repo = gh_token.get_repo(owner_repo)

            pr = gh_repo.create_pull(
                title=title, body=body, head=source_branch, base=target_branch
            )
            logging.info("Pull request created")
            return pr.html_url
        except Exception as e:
            msg = f"Could not create pull request: {e}"
            logging.error(msg)
            raise Exception(msg)
