#!/usr/bin/env python3
"""
Warning & Notification System for AI-approved cleanup actions.

READ-ONLY / NOTIFICATION-ONLY MODULE:
  - Never deletes, moves, or compresses files.
  - Converts a list of AI-approved actions into a human-readable
    warning report, assigns a severity level, logs everything to a
    review queue (so nothing is lost between runs), and sends an
    alert to the admin.
  - Every plan is stamped status = "pending_review" so a future
    deletion-automation module can pick it up later without any
    changes to this file.

Subtask map:
  4.1 build_plans() / format_report_text()   -> human-readable report
  4.2 ConsoleNotifier/EmailNotifier/etc.      -> send the alert
  4.3 determine_severity()                    -> critical / advisory
  4.4 log_to_review_queue()                   -> append-only JSONL log
  4.5 status="pending_review" on every plan   -> placeholder for later
"""

import json
import sys
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------
# 4.3 — Severity rules
# --------------------------------------------------------------------------

DEFAULT_DISK_THRESHOLD_PERCENT = 90  # at/above this -> "critical"


def determine_severity(disk_usage_percent, threshold=DEFAULT_DISK_THRESHOLD_PERCENT):
    """
    "critical" -> disk usage at/above threshold, admin should act fast
    "advisory" -> disk usage healthy, this is just informational
    """
    if disk_usage_percent is None:
        return "advisory"
    return "critical" if disk_usage_percent >= threshold else "advisory"


# --------------------------------------------------------------------------
# 4.1 — Build the human-readable warning report
# --------------------------------------------------------------------------

def humanize_size(num_bytes):
    num_bytes = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{int(num_bytes)}{unit}" if unit == "B" else f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}PB"


def build_plans(actions, severity):
    """
    Turn raw AI-approved actions into 'plans' — the structured,
    per-file record this module works with. Nothing is executed here.
    """
    plans = []
    for action in actions:
        plans.append({
            "path": action["path"],
            "size_bytes": action.get("size_bytes", 0),
            "size_human": humanize_size(action.get("size_bytes", 0)),
            "age_days": action.get("age_days"),
            "reason": action.get("reason", "unspecified"),
            "recommended_action": action.get("action", "delete"),
            "severity": severity,
            "status": "pending_review",  # 4.5 placeholder for future automation
            "flagged_at": datetime.now(timezone.utc).isoformat(),
        })
    return plans


def format_report_text(plans, disk_usage_percent, threshold):
    lines = []
    lines.append("=" * 70)
    lines.append("FILE CLEANUP WARNING REPORT (informational only — nothing deleted)")
    lines.append("=" * 70)
    lines.append(f"Generated:         {datetime.now(timezone.utc).isoformat()}")
    if disk_usage_percent is not None:
        lines.append(f"Disk usage:        {disk_usage_percent:.1f}%  (threshold: {threshold}%)")
    lines.append(f"Files flagged:     {len(plans)}")
    total_bytes = sum(p["size_bytes"] for p in plans)
    lines.append(f"Total reclaimable: {humanize_size(total_bytes)}")
    lines.append("-" * 70)

    for i, p in enumerate(plans, 1):
        lines.append(f"[{i}] {p['path']}")
        lines.append(f"    size:      {p['size_human']}")
        lines.append(f"    age:       {p['age_days']} days")
        lines.append(f"    reason:    {p['reason']}")
        lines.append(f"    action:    {p['recommended_action']}  (RECOMMENDED — not executed)")
        lines.append(f"    severity:  {p['severity']}")
        lines.append(f"    status:    {p['status']}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("No files were deleted or modified by this report.")
    lines.append("=" * 70)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 4.4 — Review queue logging (append-only, nothing lost between runs)
# --------------------------------------------------------------------------

def log_to_review_queue(plans, queue_path):
    """Append every flagged plan to a JSONL queue. Existing entries untouched."""
    queue_path = Path(queue_path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as f:
        for plan in plans:
            f.write(json.dumps(plan) + "\n")
    return queue_path


# --------------------------------------------------------------------------
# 4.2 — Alert senders (email / Slack / webhook / console)
# --------------------------------------------------------------------------

class ConsoleNotifier:
    """Always works, no config needed — default/fallback channel."""
    def send(self, subject, body):
        print(f"\n--- ALERT ({subject}) ---")
        print(body)
        return True


class EmailNotifier:
    def __init__(self, smtp_host, smtp_port, username, password, from_addr, to_addrs):
        self.smtp_host, self.smtp_port = smtp_host, smtp_port
        self.username, self.password = username, password
        self.from_addr, self.to_addrs = from_addr, to_addrs

    def send(self, subject, body):
        msg = MIMEText(body)
        msg["Subject"], msg["From"], msg["To"] = subject, self.from_addr, ", ".join(self.to_addrs)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            return True
        except Exception as e:
            print(f"[EmailNotifier] failed to send: {e}", file=sys.stderr)
            return False


class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send(self, subject, body):
        payload = {"text": f"*{subject}*\n```{body}```"}
        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.URLError as e:
            print(f"[SlackNotifier] failed to send: {e}", file=sys.stderr)
            return False


class WebhookNotifier:
    def __init__(self, url):
        self.url = url

    def send(self, subject, body):
        payload = {"subject": subject, "body": body}
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.URLError as e:
            print(f"[WebhookNotifier] failed to send: {e}", file=sys.stderr)
            return False


def get_notifier(channel, config):
    """channel: 'console' | 'email' | 'slack' | 'webhook'. Falls back to console on bad config."""
    try:
        if channel == "email":
            return EmailNotifier(**config)
        if channel == "slack":
            return SlackNotifier(**config)
        if channel == "webhook":
            return WebhookNotifier(**config)
    except TypeError as e:
        print(f"[get_notifier] bad config for '{channel}': {e} — falling back to console", file=sys.stderr)
    return ConsoleNotifier()


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def run(action_list_path, queue_path, channel="console", channel_config=None,
        disk_usage_percent=None, threshold=DEFAULT_DISK_THRESHOLD_PERCENT):
    channel_config = channel_config or {}

    with open(action_list_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    is_wrapped = isinstance(data, dict) and "actions" in data
    actions = data["actions"] if is_wrapped else data
    if disk_usage_percent is None and is_wrapped:
        disk_usage_percent = data.get("disk_usage_percent")

    severity = determine_severity(disk_usage_percent, threshold)
    plans = build_plans(actions, severity)

    report_text = format_report_text(plans, disk_usage_percent, threshold)
    print(report_text)

    log_to_review_queue(plans, queue_path)

    notifier = get_notifier(channel, channel_config)
    subject = f"[{severity.upper()}] {len(plans)} file(s) recommended for deletion"
    notifier.send(subject, report_text)

    return plans


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Warning & Notification System (no deletion)")
    parser.add_argument("action_list", help="Path to AI-approved actions JSON")
    parser.add_argument("--queue", default="review_queue.jsonl", help="Review queue log path")
    parser.add_argument("--channel", default="console", choices=["console", "email", "slack", "webhook"])
    parser.add_argument("--disk-usage", type=float, default=None, help="Override disk usage percent")
    parser.add_argument("--threshold", type=float, default=DEFAULT_DISK_THRESHOLD_PERCENT)
    args = parser.parse_args()

    run(
        action_list_path=args.action_list,
        queue_path=args.queue,
        channel=args.channel,
        disk_usage_percent=args.disk_usage,
        threshold=args.threshold,
    )
