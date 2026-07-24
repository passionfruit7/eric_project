import yaml
import psutil
import time
import json
import socket

# -----------------------------
# Read Configuration File
# -----------------------------
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

threshold = config["disk_threshold"]
interval = config["check_interval"]

hostname = socket.gethostname()

print("=" * 50)
print("      AI Disk Checker Started")
print("=" * 50)
print(f"Hostname           : {hostname}")
print(f"Threshold          : {threshold}%")
print(f"Check Interval     : {interval} seconds")
print("=" * 50)

while True:

    # -----------------------------
    # Get Disk Usage
    # -----------------------------
    disk = psutil.disk_usage("/")
    usage = disk.percent

    print("\n----------------------------------------")
    print(f"Current Disk Usage : {usage}%")
    print(f"Configured Threshold : {threshold}%")

    # -----------------------------
    # Threshold Check
    # -----------------------------
    if usage >= threshold:

        print("\n⚠️ ALERT : Disk Usage Exceeded!")

        alert = {
            "hostname": hostname,
            "disk_usage": usage,
            "threshold": threshold,
            "status": "ALERT"
        }

        with open("alert.json", "w") as file:
            json.dump(alert, file, indent=4)

        print("✅ alert.json generated successfully.")
        print("➡️ Person 2 (File Scanner) can now read this file.")

    else:

        print("\n✅ Disk Usage is Normal.")

        normal = {
            "hostname": hostname,
            "disk_usage": usage,
            "threshold": threshold,
            "status": "NORMAL"
        }

        with open("alert.json", "w") as file:
            json.dump(normal, file, indent=4)

    print(f"\nNext check in {interval} seconds...")
    time.sleep(interval)