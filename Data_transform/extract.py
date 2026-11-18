
import pandas as pd
import json
import time

from pathlib import Path

from api_fetch import (
    fetch_movie_details,
    fetch_movie_credits
)


# ==========================================
# 1. PROJECT DIRECTORIES
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "CVS_DATA" / "id_list.csv"

RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. LOAD MOVIE ID DATASET
# ==========================================

print("\nSTREAMVAULT DATA EXTRACTION STARTED")
print("=" * 45)

movie_df = pd.read_csv(INPUT_FILE)

print("\nMovie ID Dataset:")
print(movie_df.head())

print("\nDataset Information:")
print("Total records:", len(movie_df))
print("Columns:", movie_df.columns.tolist())


# ==========================================
# 3. VALIDATE THE DATASET
# ==========================================

if "tmdb_id" not in movie_df.columns:
    raise ValueError(
        "Required column 'tmdb_id' was not found in the CSV."
    )

# Remove records without movie IDs
movie_df = movie_df.dropna(subset=["tmdb_id"]).copy()

# Convert IDs to integers
movie_df["tmdb_id"] = pd.to_numeric(
    movie_df["tmdb_id"],
    errors="coerce"
)

movie_df = movie_df.dropna(subset=["tmdb_id"])

movie_df["tmdb_id"] = movie_df["tmdb_id"].astype(int)

# Remove duplicate movie IDs
movie_df = movie_df.drop_duplicates(subset=["tmdb_id"])

print("\nAfter Validation:")
print("Valid movie IDs:", len(movie_df))
print("Unique movie IDs:", movie_df["tmdb_id"].nunique())


# ==========================================
# 4. INITIALIZE STORAGE
# ==========================================

movie_details = []
movie_credits = []
failed_movies = []


# ==========================================
# 5. FETCH DATA FROM TMDB API
# ==========================================

for index, row in movie_df.iterrows():

    movie_id = row["tmdb_id"]

    print(
        f"\nFetching movie {index + 1}/{len(movie_df)}"
        f" | TMDb ID: {movie_id}",
        flush=True
    )

    try:

        # Fetch movie information
        details = fetch_movie_details(movie_id)

        # Fetch movie cast and crew
        credits = fetch_movie_credits(movie_id)

        movie_details.append(details)
        movie_credits.append(credits)

        print(
            "SUCCESS:",
            details.get("title"),
            flush=True
        )

    except Exception as error:

        print(
            f"FAILED: Movie ID {movie_id} | {error}",
            flush=True
        )

        failed_movies.append({
            "movie_id": int(movie_id),
            "error": str(error)
        })

    # Small delay between movie requests
    time.sleep(0.25)


# ==========================================
# 6. SAVE RAW API RESPONSES
# ==========================================

details_file = RAW_DIR / "movie_details.json"

credits_file = RAW_DIR / "movie_credits.json"

failed_file = RAW_DIR / "failed_movies.json"


with open(details_file, "w", encoding="utf-8") as file:

    json.dump(
        movie_details,
        file,
        indent=4,
        ensure_ascii=False
    )


with open(credits_file, "w", encoding="utf-8") as file:

    json.dump(
        movie_credits,
        file,
        indent=4,
        ensure_ascii=False
    )


with open(failed_file, "w", encoding="utf-8") as file:

    json.dump(
        failed_movies,
        file,
        indent=4,
        ensure_ascii=False
    )


# ==========================================
# 7. EXTRACTION SUMMARY
# ==========================================

print("\n")
print("=" * 45)
print("STREAMVAULT EXTRACTION COMPLETED")
print("=" * 45)

print("Total valid movie IDs:", len(movie_df))

print("Successful movie details:", len(movie_details))

print("Successful movie credits:", len(movie_credits))

print("Failed movies:", len(failed_movies))

print("\nSaved Files:")

print(details_file)
print(credits_file)
print(failed_file)

print("\nExtraction process finished!")
