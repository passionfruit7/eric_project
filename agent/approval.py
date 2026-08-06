import json
import requests

with open("../server/reports/flagged_files.json", "r") as f:
    report = json.load(f)

for file in report["flagged_files"]:

    print("\nFile:", file["path"])
    print("Risk:", file["risk"])
    print("Recommendation:", file["recommendation"])
    print("Preview:", file["preview_command"])

    choice = input("\nApprove? (y/n): ")

    if choice.lower() == "y":

        response = requests.post(
            "http://localhost:8000/execute",
            json={
                "action": file["validated_action"],
                "path": file["path"]
            }
        )

        print(response.json())

    else:

        print("Skipped")