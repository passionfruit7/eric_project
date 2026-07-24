"""
policy.py — Core Policy Engine

Generic, reusable rules for validating filesystem-affecting actions proposed
by an AI system. This module knows nothing about any specific caller's API
contract (that lives in safety_checker.py) — it only answers two questions:

    1. Is this path safe to touch, given an allow-list and a deny-list?
    2. Does this path/command match a known-dangerous pattern?

Design principles:
    - Fail closed. Any ambiguity (unresolvable path, unknown action type,
      symlink escape, traversal) results in REJECTION, not a warning.
    - Canonicalize before comparing. Never compare raw strings; always
      resolve to an absolute, symlink-free path first.
    - Defense in depth. Even if a path is under an allowed directory,
      it is still checked against an explicit critical-file/pattern list.
"""

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger("policy_engine")


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyResult:
    allowed: bool
    risk_level: RiskLevel
    reason: str
    rule_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Critical system paths — never touchable, regardless of allow-list contents.
# This is intentionally broader than any one caller's block-list so the core
# engine stays safe even if a caller misconfigures its own allow-list.
# ---------------------------------------------------------------------------
CRITICAL_PATH_PREFIXES = [
    "/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/boot", "/root",
    "/sys", "/proc", "/dev", "/opt",
    "/home",  # user home dirs are off-limits by default for AI-initiated ops
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
    "/System", "/Library/LaunchDaemons", "/Library/LaunchAgents",
]

CRITICAL_FILENAMES = {
    "passwd", "shadow", "sudoers", "fstab", "hosts", "crontab",
    "authorized_keys", "id_rsa", "id_ed25519", "known_hosts",
}

DANGEROUS_COMMAND_PATTERNS = [
    (r"rm\s+-rf\s+/(?:\s|$)", "recursive delete of root"),
    (r"rm\s+-rf\s+~", "recursive delete of home"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "fork bomb"),
    (r"dd\s+if=.*of=/dev/(sd|nvme|hd)", "raw disk write"),
    (r"mkfs\.", "filesystem format"),
    (r"chmod\s+-R\s+777\s+/", "recursive world-writable root"),
    (r">\s*/dev/sd[a-z]", "raw device overwrite"),
    (r"curl.*\|\s*(sh|bash)", "pipe download to shell"),
    (r"wget.*\|\s*(sh|bash)", "pipe download to shell"),
    (r"\bsudo\b", "privilege escalation"),
    (r"DROP\s+(DATABASE|TABLE)", "destructive SQL"),
    (r"shutdown|reboot|init\s+0", "system power control"),
]
_DANGEROUS_COMMAND_RE = [(re.compile(p, re.IGNORECASE), why) for p, why in DANGEROUS_COMMAND_PATTERNS]


def canonicalize(raw_path: str, base: Optional[str] = None) -> str:
    """
    Resolve a path to an absolute, symlink-free, normalized form.
    Raises ValueError if the path cannot be safely resolved.
    """
    if raw_path is None:
        raise ValueError("path is None")
    if "\x00" in raw_path:
        raise ValueError("null byte in path")

    p = Path(raw_path)
    if base and not p.is_absolute():
        p = Path(base) / p

    if not p.is_absolute():
        raise ValueError(f"path is not absolute: {raw_path!r}")

    # os.path.realpath resolves '..', '.', and symlinks (even if the target
    # does not exist, it resolves as much of the chain as it can).
    resolved = os.path.realpath(str(p))
    return resolved


def is_critical_path(resolved_path: str) -> Optional[str]:
    """Return a reason string if the path is a protected system path, else None."""
    norm = resolved_path.replace("\\", "/")
    for prefix in CRITICAL_PATH_PREFIXES:
        prefix_norm = prefix.replace("\\", "/")
        if norm == prefix_norm or norm.startswith(prefix_norm.rstrip("/") + "/"):
            return f"path is under protected system directory {prefix}"

    filename = os.path.basename(norm)
    if filename in CRITICAL_FILENAMES:
        return f"filename '{filename}' matches critical-file list"

    return None


def is_within_any(resolved_path: str, allowed_dirs: Iterable[str]) -> Optional[str]:
    """Return the matching allowed-dir prefix if resolved_path is inside it, else None."""
    for d in allowed_dirs:
        allowed_resolved = os.path.realpath(d)
        if resolved_path == allowed_resolved or resolved_path.startswith(allowed_resolved.rstrip("/") + "/"):
            return allowed_resolved
    return None


def check_path(
    raw_path: str,
    allowed_dirs: Iterable[str],
    base: Optional[str] = None,
) -> PolicyResult:
    """
    Validate a single path against an allow-list, with mandatory
    critical-path protection layered on top regardless of allow-list content.
    """
    try:
        resolved = canonicalize(raw_path, base=base)
    except ValueError as e:
        return PolicyResult(False, RiskLevel.HIGH, f"path rejected: {e}", rule_id="PATH_UNRESOLVABLE")

    critical_reason = is_critical_path(resolved)
    if critical_reason:
        return PolicyResult(False, RiskLevel.CRITICAL, critical_reason, rule_id="CRITICAL_PATH")

    match = is_within_any(resolved, allowed_dirs)
    if not match:
        return PolicyResult(
            False, RiskLevel.HIGH,
            f"path '{resolved}' is not under any allowed directory",
            rule_id="OUTSIDE_ALLOWLIST",
        )

    return PolicyResult(True, RiskLevel.SAFE, f"path within allowed directory {match}", rule_id="OK")


def check_command(command: str) -> PolicyResult:
    """Check a shell-command-like string against known-dangerous patterns."""
    if command is None:
        return PolicyResult(False, RiskLevel.HIGH, "command is None", rule_id="EMPTY_COMMAND")
    for pattern, why in _DANGEROUS_COMMAND_RE:
        if pattern.search(command):
            return PolicyResult(False, RiskLevel.CRITICAL, f"matched dangerous pattern: {why}", rule_id="DANGEROUS_COMMAND")
    return PolicyResult(True, RiskLevel.SAFE, "no dangerous pattern matched", rule_id="OK")
