import os
import requests

from dotenv import load_dotenv
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

ACCESS_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

if not ACCESS_TOKEN:
    raise ValueError("API_READ_ACCESS_TOKEN is missing from .env")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "accept": "application/json",
})

# Retry temporary failures only (404 is permanent and is NOT retried)
retry_strategy = Retry(
    total=4,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
session.mount("https://", adapter)


def _get(path, params=None):
    response = session.get(f"{BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_movie_details(movie_id):
    return _get(f"/movie/{movie_id}", {"language": "en-US"})


def fetch_movie_credits(movie_id):
    return _get(f"/movie/{movie_id}/credits", {"language": "en-US"})


def resolve_imdb_id(imdb_id):
    """Map an IMDb id (tt...) to a TMDb movie id. Returns None if no match."""
    result = _get(f"/find/{imdb_id}", {"external_source": "imdb_id"})
    matches = result.get("movie_results", [])
    return matches[0]["id"] if matches else None