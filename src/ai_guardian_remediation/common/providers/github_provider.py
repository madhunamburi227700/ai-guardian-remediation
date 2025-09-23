from urllib.parse import urlparse
import logging
from github import Github
from ai_guardian_remediation.core.agents.cve_remediation.claude_code.prompts import PULL_REQUEST_PROMPT

class GithubProvider():
    def __init__(self, git_manager, repo_url, clone_path, branch=None, token=None):
        self.git_manager = git_manager
        self.repo_url = repo_url
        self.clone_path = clone_path
        self.token = token
        self.branch = branch or self.get_default_branch()

    @staticmethod
    def extract_owner_repo(url):
        parsed = urlparse(url)
        path = parsed.path
        if path.endswith(".git"):
            path = path[:-4]
        return path.strip("/")
    
    def create_pull_request(self, main_branch_name, cve_id, package):
        try:
            fix_branch = self.git_manager.fix_branch
            gh_token = Github(self.token)
            owner_repo = GithubProvider.extract_owner_repo(self.repo_url)
            gh_repo = gh_token.get_repo(owner_repo)

            body = PULL_REQUEST_PROMPT.format(
                cve_id=cve_id, 
                package=package
            )

            title = f"fix: {cve_id}"

            pr = gh_repo.create_pull(
                title=title,
                body=body,
                head=fix_branch,
                base=main_branch_name
            )
            logging.info('Pull request created')
        except Exception as e:
            logging.error(f'Could not create pull request: {e}')