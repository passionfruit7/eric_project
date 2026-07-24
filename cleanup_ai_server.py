"""
main.py — AI Decision Engine (Task 2)

Exposes POST /cleanup-plan
Input:  JSON file list from the File Finder (Task 1's output)
Output: JSON list of proposed actions (delete/compress) for the
        Safety Checker (Task 3) to validate before anything runs.

This module does NOT delete or compress anything itself — it only
asks the model what it recommends. Safety Checker has final say.
"""

import json
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AI Cleanup Decision Engine")

# --- Config -----------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b-instruct"   # swap for llama3.1:8b-instruct etc. if you want to compare
REQUEST_TIMEOUT_SECONDS = 120

PROTECTED_PATHS = ["/etc", "/usr", "/home", "/bin", "/lib"]
ALLOWED_TYPES = ["log", "cache", "tmp", "backup", "iso"]

# --- Request/response schemas ------------------------------------------
class FileEntry(BaseModel):
    path: str
    size_mb: float
    age_days: int
    type: Optional[str] = "unknown"


class CleanupRequest(BaseModel):
    hostname: str
    scanned_at: Optional[str] = None
    files: List[FileEntry]


# --- Prompt --------------------------------------------------------------
SYSTEM_PROMPT = """You are a Linux storage optimization assistant.

Goal: recommend which files below are safe to delete or compress to free disk space.

Rules:
- NEVER recommend any action on files under these paths: /etc, /usr, /home, /bin, /lib
- Only recommend action on files of type: log, cache, tmp, backup, iso
- Prefer "compress" for large log files that might still be useful
- Prefer "delete" for old temp files, isos, and stale backups
- If a file looks important or you are unsure, do not include it

Return JSON only, in exactly this shape, with no extra text before or after it:
{"actions": [{"action": "delete", "path": "/tmp/example.iso", "reason": "short reason"}]}

If no files qualify, return: {"actions": []}
"""


def build_prompt(files: List[FileEntry]) -> str:
    file_list_str = json.dumps([f.dict() for f in files], indent=2)
    return f"{SYSTEM_PROMPT}\n\nFiles:\n{file_list_str}"


def call_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",   # tells Ollama to constrain output to valid JSON
        "stream": False,
        "options": {
            "temperature": 0   # deterministic output: same input -> same decision every time
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {e}")

    data = resp.json()
    return data.get("response", "")


@app.post("/cleanup-plan")
def cleanup_plan(req: CleanupRequest):
    if not req.files:
        return {"actions": []}

    prompt = build_prompt(req.files)
    raw_output = call_ollama(prompt)

    try:
        plan = json.loads(raw_output)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail=f"Model did not return valid JSON. Raw output: {raw_output[:300]}"
        )

    if "actions" not in plan or not isinstance(plan["actions"], list):
        raise HTTPException(status_code=502, detail="Model response missing an 'actions' list")

    return plan


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}
