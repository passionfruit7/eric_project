from fastapi import FastAPI
from planner import generate_plan
from registration import register_server

app = FastAPI()


@app.get("/")
def home():

    return {

        "message": "Linux Optimizer Server Running"

    }


@app.post("/register")
def register(data: dict):

    return register_server(

        data["hostname"],

        data["ip"],

        data["threshold"]

    )


@app.post("/cleanup-plan")
def cleanup(data: dict):

    return generate_plan(data)


@app.post("/execute")
def execute(data: dict):

    from executor import execute_action

    return execute_action(
        data["action"],
        data["path"]
    )
