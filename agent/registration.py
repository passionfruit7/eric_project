import socket
import requests
import yaml


def register():

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    ip = requests.get("https://api.ipify.org").text

    payload = {
        "hostname": socket.gethostname(),
        "ip": ip,
        "threshold": config["disk_threshold"]
    }

    try:
        response = requests.post(
            f"{config['server_url']}/register",
            json=payload
        )

        print(response.json())

    except Exception as e:
        print("Registration failed:", e)