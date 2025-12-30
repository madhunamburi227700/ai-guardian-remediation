import os
import logging
import shutil
from datetime import datetime, timedelta

CLONE_TMP_DIRECTORY = "clone-tmp"


def cleanup_dirs():
    now = datetime.now()
    cutoff = now - timedelta(days=3)

    if not os.path.exists(CLONE_TMP_DIRECTORY):
        logging.info(
            f"Directory {CLONE_TMP_DIRECTORY} does not exist. No cleanup needed."
        )
        return

    logging.info(f"Checking for repos older than {cutoff}")

    for top_level in os.listdir(CLONE_TMP_DIRECTORY):
        top_level_path = os.path.join(CLONE_TMP_DIRECTORY, top_level)

        if not os.path.isdir(top_level_path):
            continue

        # Go one level deeper
        for sub in os.listdir(top_level_path):
            sub_path = os.path.join(top_level_path, sub)

            if os.path.isdir(sub_path):
                mod_time = datetime.fromtimestamp(os.path.getmtime(sub_path))
                if mod_time < cutoff:
                    logging.info(
                        f"Deleting subdirectory: {sub_path} last modified at {mod_time}"
                    )
                    shutil.rmtree(sub_path)
