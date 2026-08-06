import subprocess


def execute_action(action, path):

    commands = {
        "archive": f"gzip {path}",
        "compress": f"tar -czf {path}.tar.gz {path}",
        "delete": f"rm -f {path}"
    }

    command = commands.get(action)

    if not command:

        return {
            "status": "error",
            "message": "Unknown action"
        }

    return {
        "status": "pending",
        "command": command
    }