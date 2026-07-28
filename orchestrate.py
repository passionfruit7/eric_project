import json
import subprocess
import sys
from pathlib import Path

import requests

from safety_checker import process_cleanup_plan
import warning_system

AI_ENDPOINT = "http://localhost:8000/cleanup-plan"
ALERT_PATH = "alert.json"
FILES_PATH = "files.json"
REVIEW_QUEUE_PATH = "review_queue.jsonl"
ENRICHED_PATH = "enriched_actions.json"


def main():
    alert = json.loads(Path(ALERT_PATH).read_text())
    print(f"Disk status: {alert['status']} ({alert['disk_usage']}%)")
    if alert["status"] != "ALERT":
        print("Disk usage below threshold — nothing to do.")
        return

    print("\n[1/4] Running File Finder...")
    subprocess.run([sys.executable, "filef.py", "--output", FILES_PATH], check=True)
    files_data = json.loads(Path(FILES_PATH).read_text())
    files_by_path = {f["path"]: f for f in files_data["files"]}

    if not files_data["files"]:
        print("No candidate files found. Try lowering --min-size-mb/--min-age-days.")
        return

    print("\n[2/4] Calling AI Decision Engine...")
    resp = requests.post(AI_ENDPOINT, json=files_data, timeout=120)
    resp.raise_for_status()
    plan = resp.json()
    print("AI proposed:", json.dumps(plan, indent=2))

    print("\n[3/4] Validating through Safety Checker...")
    checked = process_cleanup_plan(plan)
    print(f"Approved: {len(checked['approved'])}  Rejected: {len(checked['rejected'])}")
    for r in checked["rejected"]:
        print(f"  REJECTED {r['path']}: {r['rejection_reason']}")

    if not checked["approved"]:
        print("Nothing approved — stopping before Warning System.")
        return

    enriched = []
    for a in checked["approved"]:
        original = files_by_path.get(a["path"], {})
        enriched.append({
            "path": a["path"],
            "action": a["action"],
            "reason": a["reason"],
            "size_bytes": int(original.get("size_mb", 0) * 1024 * 1024),
            "age_days": original.get("age_days"),
        })

    Path(ENRICHED_PATH).write_text(json.dumps({
        "disk_usage_percent": alert["disk_usage"],
        "actions": enriched,
    }, indent=2))

    print("\n[4/4] Generating warning report...")
    warning_system.run(
        action_list_path=ENRICHED_PATH,
        queue_path=REVIEW_QUEUE_PATH,
        channel="console",
        disk_usage_percent=alert["disk_usage"],
        threshold=alert.get("threshold", 85),
    )


if __name__ == "__main__":
    main()