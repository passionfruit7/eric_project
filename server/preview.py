def generate_preview(file):

    action = file["validated_action"]
    path = file["path"]

    if action == "archive":
        return f"gzip {path}"

    elif action == "compress":
        return f"gzip {path}"

    elif action == "delete":
        return f"rm {path}"

    return "No action"