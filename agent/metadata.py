import os
from datetime import datetime


def get_metadata(path):

    try:

        stat = os.stat(path)

        return {

            "size_mb": round(
                stat.st_size / (1024 * 1024), 2
            ),

            "modified": datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%Y-%m-%d"),

            "accessed": datetime.fromtimestamp(
                stat.st_atime
            ).strftime("%Y-%m-%d"),

            "uid": stat.st_uid
        }

    except Exception as e:

        print(f"Metadata error: {e}")

        return None