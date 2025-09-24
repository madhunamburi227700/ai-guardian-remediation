import os
import logging
import shutil
from datetime import datetime, timedelta

CLONE_TMP_DIRECTORY = "clone-tmp"


def cleanup_dirs():
    now = datetime.now()
    cutoff = now - timedelta(hours=12)

    logging.info(f"Checking for repos older than {cutoff}")

    for repo_name in os.listdir(CLONE_TMP_DIRECTORY):
        repo_path = os.path.join(CLONE_TMP_DIRECTORY, repo_name)
        if os.path.isdir(repo_path):
            mod_time = datetime.fromtimestamp(os.path.getmtime(repo_path))
            if mod_time < cutoff:
                logging.info(
                    f"Deleting repository: {repo_name} last modified at {mod_time}"
                )
                shutil.rmtree(repo_path)
