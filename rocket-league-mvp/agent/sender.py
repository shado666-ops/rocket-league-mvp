import requests


API_URL = "http://127.0.0.1:8000/api/matches"


def send_match(payload: dict) -> dict:
    response = requests.post(API_URL, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()