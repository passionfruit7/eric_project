import os
import time

from metadata import get_metadata
from user_mapper import get_owner
from user_mapper import is_system_user


def scan(scan_paths, min_size_mb):

    flagged_files = []

    current_time = time.time()

    for scan_path in scan_paths:

        if not os.path.exists(scan_path):
            print(f"Skipping {scan_path} (does not exist)")
            continue

        print(f"Scanning {scan_path} ...")

        for root, dirs, files in os.walk(scan_path):

            for file_name in files:

                path = os.path.join(root, file_name)

                try:

                    metadata = get_metadata(path)

                    if metadata is None:
                        continue

                    size_mb = metadata["size_mb"]

                    if size_mb < min_size_mb:
                        continue

                    age_days = int(

                        (current_time - os.path.getmtime(path))
                        / (60 * 60 * 24)

                    )

                    uid = metadata["uid"]

                    owner = get_owner(uid)

                    protected = is_system_user(uid)

                    # Skip system users

                    if protected:
                        continue

                    # Skip recent files

                    if age_days < 90:
                        continue

                    file_type = "unknown"

                    if "." in file_name:
                        file_type = file_name.split(".")[-1]

                    flagged_files.append(

                        {

                            "hostname": os.uname().nodename,

                            "path": path,

                            "size_mb": size_mb,

                            "days_old": age_days,

                            "owner": owner,

                            "uid": uid,

                            "protected_user": protected,

                            "modified": metadata["modified"],

                            "accessed": metadata["accessed"],

                            "type": file_type

                        }

                    )

                except Exception as e:

                    print(f"Error scanning {path}: {e}")

                    continue

    print(f"\nTotal flagged files: {len(flagged_files)}")

    return flagged_files