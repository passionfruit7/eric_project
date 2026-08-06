import requests


def send_report(server_url, payload):

    response = requests.post(

        f"{server_url}/cleanup-plan",

        json=payload
    )

    return response.json()