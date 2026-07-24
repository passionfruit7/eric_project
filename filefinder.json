import argparse
import json
import os
import platform
import socket
import tempfile
import time


def default_paths():
    system = platform.system()
    if system == "Linux":
        return ["/tmp", "/var/log", "/backup"]
    elif system == "Windows":
        return [tempfile.gettempdir()]
    else:
        return [tempfile.gettempdir()]


def parse_args():
    p = argparse.ArgumentParser(description="Find large, old files and export as JSON.")
    p.add_argument("--path", action="append",
                    help="Folder to scan. Repeatable. Default: OS-appropriate folders")
    p.add_argument("--min-size-mb", type=float, default=50.0,
                    help="Ignore files smaller than this (MB). Default: 50")
    p.add_argument("--min-age-days", type=int, default=30,
                    help="Ignore files newer than this (days). Default: 30")
    p.add_argument("--output", default="files.json",
                    help="Output JSON file path. Default: files.json")
    return p.parse_args()


def classify_type(path: str) -> str:
    lower = path.lower().replace("\\", "/")
    if lower.endswith(".log") or "/var/log" in lower:
        return "log"
    if lower.endswith(".tmp") or "/tmp/" in lower or "/temp/" in lower:
        return "tmp"
    if "cache" in lower:
        return "cache"
    if "backup" in lower or lower.endswith(".bak"):
        return "backup"
    if lower.endswith(".iso"):
        return "iso"
    return "unknown"


def scan(paths, min_size_mb, min_age_days):
    now = time.time()
    results = []

    for root_path in paths:
        if not os.path.isdir(root_path):
            print(f"Skipping (not found): {root_path}")
            continue

        for dirpath, _, filenames in os.walk(root_path, onerror=lambda e: None):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.lstat(fpath)
                except (OSError, PermissionError):
                    continue

                if not os.path.isfile(fpath):
                    continue
                if hasattr(os.path, "islink") and os.path.islink(fpath):
                    continue

                size_mb = round(st.st_size / (1024 * 1024), 2)
                age_days = int((now - st.st_mtime) / 86400)

                if size_mb < min_size_mb or age_days < min_age_days:
                    continue

                results.append({
                    "path": fpath,
                    "size_mb": size_mb,
                    "age_days": age_days,
                    "type": classify_type(fpath),
                })

    return results


def main():
    args = parse_args()
    paths = args.path or default_paths()

    files = scan(paths, args.min_size_mb, args.min_age_days)

    output = {
        "hostname": socket.gethostname(),
        "files": files,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"OS detected: {platform.system()}")
    print(f"Scanned: {paths}")
    print(f"Found {len(files)} candidate file(s) matching filters")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
