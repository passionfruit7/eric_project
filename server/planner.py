import json

from scoring import calculate_score

from ollama_client import ask_llm

from policy_engine import validate

from preview import generate_preview

def generate_plan(data):

    scored_files = []

    for file in data["files"]:

        score_data = calculate_score(file)

        file["score"] = score_data["score"]

        file["risk"] = score_data["risk"]

        raw_recommendation = ask_llm(file)

        file["recommendation"] = raw_recommendation

        file["validated_action"] = validate(file)

        file["preview_command"] = generate_preview(file)

        scored_files.append(file)

    report = {

        "hostname": data["hostname"],

        "disk_usage": data["disk_usage"],

        "flagged_files": scored_files

    }

    with open(

        "reports/flagged_files.json",

        "w"

    ) as f:

        json.dump(

            report,

            f,

            indent=4

        )

    return {

        "status": "success",

        "hostname": data["hostname"],

        "files_received": len(scored_files)

    }