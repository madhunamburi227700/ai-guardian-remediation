from urllib.parse import urlparse
import json
import re
import hashlib
import random
import string


def get_clone_directory_name(repo_url: str, *args):
    repo_name = get_repo_name_from_url(repo_url)
    path = "-".join([repo_url] + list(arg if arg is not None else "" for arg in args))
    return f"{repo_name}-{calculate_sha256_of_string(path)}"


def get_repo_name_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    repo_name = parsed_url.path.strip("/").split("/")[-1]

    # Remove ".git" from the repo name if present
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return repo_name


def calculate_sha256_of_string(input_string: str) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_string.encode("utf-8"))
    return sha256_hash.hexdigest()


def format_stream_data(data) -> str:
    return f"data: {json.dumps(data)}\n\n"


def sanitize_github_url(url: str) -> str | None:
    """
    Sanitize a GitHub URL.
    - Ensures it ends with `.git`
    - Returns None if not a valid GitHub repository URL

    Args:
        url (str): The input URL

    Returns:
        str | None: Sanitized URL or None if invalid
    """
    pattern = r"^https://github\.com/[^/]+/[^/]+(?:\.git)?$"

    if not re.match(pattern, url):
        return None

    if not url.endswith(".git"):
        return url + ".git"

    return url


def detect_provider(remote_url):
    url = remote_url.lower()

    if "github.com" in url:
        return "github"
    else:
        return "unknown"


def generate_repo_url(platform: str, organization: str, repository: str) -> str:
    # Check if the platform is GitHub
    if platform.lower() != "github":
        raise ValueError("The platform must be GitHub.")

    # Construct the GitHub repository URL
    repo_url = f"https://github.com/{organization}/{repository}"
    return repo_url


# CVE utils
def create_branch_name_for_cve_remediation(cve_id, package):
    characters = string.ascii_letters + string.digits
    random_string = "".join(random.choice(characters) for _ in range(10))
    branch_name = f"fix/{cve_id}-{package}-{random_string}"
    return branch_name


# SAST utils
def create_branch_name_for_sast_remediation(rule_id, line_no):
    characters = string.ascii_letters + string.digits
    random_string = "".join(random.choice(characters) for _ in range(10))
    branch_name = f"fix/{rule_id}-{line_no}-{random_string}"
    return branch_name
