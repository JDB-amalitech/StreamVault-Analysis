
import os
import requests

from dotenv import load_dotenv
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Locate the project's root directory
BASE_DIR = Path(__file__).resolve().parents[1]

# Load environment variables
load_dotenv(BASE_DIR / ".env")

ACCESS_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")

BASE_URL = "https://api.themoviedb.org/3"

if not ACCESS_TOKEN:
    raise ValueError("API_READ_ACCESS_TOKEN is missing from .env")


# Configure the API session
session = requests.Session()

session.headers.update({
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "accept": "application/json"
})

# Retry temporary failures
retry_strategy = Retry(
    total=4,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("https://", adapter)


def fetch_movie_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    response = session.get(
        url,
        params={"language": "en-US"},
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def fetch_movie_credits(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}/credits"

    response = session.get(
        url,
        params={"language": "en-US"},
        timeout=30
    )

    response.raise_for_status()

    return response.json()
