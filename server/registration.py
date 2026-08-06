import json
import os


REGISTRY_FILE = "servers.json"


def register_server(hostname, ip, threshold):

    if not os.path.exists(REGISTRY_FILE):

        with open(REGISTRY_FILE, "w") as f:
            json.dump([], f)

    with open(REGISTRY_FILE, "r") as f:
        servers = json.load(f)

    for server in servers:

        if server["hostname"] == hostname:

            return {
                "status": "already_registered"
            }

    servers.append(

        {
            "hostname": hostname,
            "ip": ip,
            "threshold": threshold
        }

    )

    with open(REGISTRY_FILE, "w") as f:

        json.dump(servers, f, indent=4)

    return {

        "status": "registered",

        "hostname": hostname

    }