import requests

BASE_URL = "https://nominatim.openstreetmap.org/search"


def geocode(address: str):
    response = requests.get(
        BASE_URL,
        params={
            "q": address,
            "format": "json",
            "limit": 1,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return (
        float(data[0]["lat"]),
        float(data[0]["lon"]),
    )