import os
from fastapi import Header, HTTPException

API_TOKEN = os.environ["CITYMED_API_TOKEN"]


def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid bearer token.")
    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        raise HTTPException(
            status_code=401, detail="Missing or invalid bearer token.")
