import requests


def ask_llm(file):

    prompt = f"""
You are a Linux optimization assistant.

Analyze this file:

Path: {file['path']}
Size: {file['size_mb']} MB
Age: {file['days_old']} days
Type: {file['type']}
Owner: {file['owner']}
Risk: {file['risk']}

Choose exactly one:

- archive
- compress
- ignore

Give one sentence only.
"""

    response = requests.post(

        "http://localhost:11434/api/generate",

        json={

            "model": "qwen2.5:0.5b",

            "prompt": prompt,

            "stream": False

        }

    )

    return response.json()["response"]