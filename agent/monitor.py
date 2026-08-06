import time
import yaml
import psutil
import requests
import socket
import approval
from registration import register

from scanner import scan


with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
register()

while True:

    usage = psutil.disk_usage("/").percent

    print(f"Current disk usage: {usage}%")

    if usage >= config["disk_threshold"]:
        files = scan(

            config["scan_paths"],

            config["min_size_mb"]
        )

        payload = {

            "hostname": socket.gethostname(),

            "disk_usage": usage,

            "target_usage": config["target_usage"],

            "files": files
        }

        response = requests.post(

            f"{config['server_url']}/cleanup-plan",

            json=payload
        )

        print(response.json())

    time.sleep(config["scan_interval"])