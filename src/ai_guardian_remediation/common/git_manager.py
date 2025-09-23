import git
import shutil
import os
from urllib.parse import urlparse
import logging
import uuid
import random
import string

class GitRepoManager:
    def __init__(self, repo_url, clone_path, branch=None, token=None):
        self.repo_url = repo_url
        self.clone_path = clone_path
        self.token = token
        self.branch = branch or self.get_default_branch()
        self.fix_branch = None

    def _get_authenticated_url(self):
        if self.token:
            # HTTPS with token authentication
            parsed_url = urlparse(self.repo_url)
            netloc = parsed_url.netloc
            path = parsed_url.path.strip("/")
            return f"https://{self.token}@{netloc}/{path}"
        else:
            raise ValueError("No authentication method provided (token required).")

    def get_default_branch(self) -> str:
        """Get the default branch of the remote repository."""
        try:
            authenticated_url = self._get_authenticated_url()
            remote_refs = git.cmd.Git().ls_remote("--symref", authenticated_url, "HEAD")
            for line in remote_refs.splitlines():
                if line.startswith("ref:") and "HEAD" in line:
                    return line.split()[1].split("/")[-1]
            return None
        except Exception as e:
            (f"Failed to get default branch: {e}")
            return None

    def clone_repo(self) -> bool:
        is_cloned = False
        if os.path.exists(self.clone_path):
            logging.debug(
                f"Repository already exists at {self.clone_path}. Cleaning it for a fresh clone operation."
            )
            self.cleanup_repo()

        try:
            authenticated_url = self._get_authenticated_url()
            logging.info(
                f"Cloning repository from {self.repo_url}, branch {self.branch} to {self.clone_path}..."
            )

            if self.token:
                # Get default branch if not specified
                # branch_to_clone = self.branch or self.get_default_branch()

                # Clone with single branch option
                git.Repo.clone_from(
                    authenticated_url,
                    self.clone_path,
                    branch=self.branch,
                    single_branch=True,
                    depth=1,  # Also limit history to latest commit
                )

            logging.info(f"Repository successfully cloned to {self.clone_path}.")
            is_cloned = True
            # Remove token from remote URL after clone
            try:
                repo = git.Repo(self.clone_path)
                repo.remotes.origin.set_url(self.repo_url)
                logging.info(f"Remote URL reset to {self.repo_url} (token removed).")
            except Exception as e:
                logging.error(f"Failed to reset remote URL: {e}")
            return is_cloned
        except Exception as e:
            logging.error(f"Failed to clone repository: {e}")
            return is_cloned

    def cleanup_repo(self):
        if os.path.exists(self.clone_path):
            try:
                logging.info(f"Cleaning up the repository at {self.clone_path}...")
                shutil.rmtree(self.clone_path)
                logging.info("Repository cleaned up successfully.")
            except Exception as e:
                logging.error(f"Failed to clean up repository: {e}")
        else:
            logging.info("No repository found to clean up.")

    def calculate_branch_diff(self, branch_name):
        try:
            repo = git.Repo(self.clone_path)
            if branch_name not in repo.heads:
                raise ValueError(
                    f"Branch '{branch_name}' does not exist in the repository."
                )

            branch = repo.heads[branch_name]
            diff = repo.git.diff(branch.commit)
            return diff
        except Exception as e:
            logging.error(f"Failed to calculate diff for branch '{branch_name}': {e}")
            return None

    def get_current_branch(self):
        try:
            repo = git.Repo(self.clone_path)
            return repo.active_branch.name
        except TypeError:
            logging.error("Detached HEAD state: Not currently on any branch.")
            return None
        except Exception as e:
            logging.error(f"Failed to get the current branch: {e}")
            return None
        
    @staticmethod
    def create_branch_name(cve_id, package):
        characters = string.ascii_letters + string.digits
        random_string =  ''.join(random.choice(characters) for _ in range(10))
        branch_name = 'fix/' + cve_id + '_' + package + '_' + random_string
        return branch_name
           
    def commit_to_branch(self, main_branch_name, cve_id, package):
        try:
            random_uuid = str(uuid.uuid4())
            self.fix_branch = GitRepoManager.create_branch_name(cve_id, package)

            repo = git.Repo(self.clone_path)
            repo.git.checkout("HEAD", b=self.fix_branch)

            repo.git.add(A=True)
            repo.index.commit(f"Remediation for {cve_id}")

            origin = repo.remote(name='origin')
            origin.push(refspec=f"{self.fix_branch}:{self.fix_branch}")
            logging.info(f'Pushed changes to new branch {self.fix_branch}')
        except Exception as e:
            logging.error(f'Could not changes to new branch: {e}')

    @staticmethod
    def cleanup_all_repos(folder_path):
        if os.path.exists(folder_path):
            try:
                logging.info(
                    f"Cleaning up all repositories in the folder: {folder_path}..."
                )
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logging.info(f"Cleaned up repository: {item_path}")
                logging.info("All repositories cleaned up successfully.")
            except Exception as e:
                logging.error(f"Failed to clean up repositories in the folder: {e}")
        else:
            logging.error(f"Folder {folder_path} does not exist.")
