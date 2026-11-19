"""
Extraction: id_list.csv -> raw TMDb JSON + a ledger that accounts for
EVERY input row (fetched / duplicate / invalid / missing / not found).

Re-runnable: films already stored in data/raw are not fetched again, so a
crash or a 500-title run can resume where it stopped.
"""
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import config as cfg
from utils import read_json, write_json
from api_fetch import fetch_movie_details, fetch_movie_credits, resolve_imdb_id


# ------------------------------------------------------------------
# 1. LOAD IDS AS TEXT (never coerce silently: that is how rows vanish)
# ------------------------------------------------------------------
def load_id_list():
    df = pd.read_csv(cfg.INPUT_FILE, dtype=str, skip_blank_lines=False)
    if "tmdb_id" not in df.columns:
        raise ValueError("Required column 'tmdb_id' was not found in the CSV.")
    df = df[["tmdb_id"]].copy()
    df.insert(0, "input_row", range(1, len(df) + 1))
    df["raw_id"] = df["tmdb_id"].str.strip()
    return df.drop(columns="tmdb_id")


def classify_ids(df):
    """Vectorised classification of every raw id."""
    raw = df["raw_id"]
    is_blank = raw.isna() | (raw == "")
    is_imdb = raw.str.fullmatch(r"tt\d+", na=False)
    num = pd.to_numeric(raw.where(~is_imdb), errors="coerce")
    is_valid_num = num.notna() & (num > 0) & (num % 1 == 0)

    df["id_kind"] = "unparseable"
    df.loc[is_valid_num, "id_kind"] = "tmdb"
    df.loc[is_imdb, "id_kind"] = "imdb"
    df.loc[num.notna() & ~is_valid_num, "id_kind"] = "invalid_number"
    df.loc[is_blank, "id_kind"] = "missing"
    df["tmdb_id"] = num.where(is_valid_num).astype("Int64")
    return df


def resolve_imdb_ids(df):
    """Recover rows holding an IMDb id instead of a TMDb id."""
    for idx in df.index[df["id_kind"] == "imdb"]:
        try:
            df.at[idx, "tmdb_id"] = resolve_imdb_id(df.at[idx, "raw_id"])
        except Exception as error:
            print(f"IMDb lookup failed for {df.at[idx, 'raw_id']}: {error}")
    return df


def flag_duplicates(df):
    usable = df["tmdb_id"].notna()
    df["is_duplicate"] = usable & df.duplicated("tmdb_id", keep="first")
    return df


# ------------------------------------------------------------------
# 2. FETCH (concurrent, resumable)
# ------------------------------------------------------------------
def fetch_one(movie_id):
    try:
        details = fetch_movie_details(movie_id)
        credits = fetch_movie_credits(movie_id)
        return movie_id, details, credits, None
    except Exception as error:
        return movie_id, None, None, str(error)


def main():
    start = time.perf_counter()
    print("\nSTREAMVAULT DATA EXTRACTION STARTED")
    print("=" * 45)

    ids = load_id_list()
    ids = classify_ids(ids)
    ids = resolve_imdb_ids(ids)
    ids = flag_duplicates(ids)

    to_fetch = ids.loc[ids["tmdb_id"].notna() & ~ids["is_duplicate"],
                       "tmdb_id"].astype(int).tolist()

    # Resume: keep what is already stored
    details = {d["id"]: d for d in read_json(cfg.DETAILS_FILE)}
    credits = {c["id"]: c for c in read_json(cfg.CREDITS_FILE)}
    have = set(details) & set(credits)
    pending = [i for i in to_fetch if i not in have]
    print(f"Input rows: {len(ids)} | unique valid ids: {len(to_fetch)} "
          f"| already stored: {len(to_fetch) - len(pending)} "
          f"| to fetch: {len(pending)}")

    failures = {}
    with ThreadPoolExecutor(max_workers=cfg.MAX_WORKERS) as pool:
        for n, (mid, det, cred, err) in enumerate(pool.map(fetch_one, pending), 1):
            if err:
                failures[mid] = err
                print(f"FAILED  {mid} | {err}", flush=True)
            else:
                details[mid], credits[mid] = det, cred
                print(f"OK      {mid} | {det.get('title')}", flush=True)
            if n % cfg.SAVE_EVERY == 0:      # checkpoint
                write_json(cfg.DETAILS_FILE, list(details.values()))
                write_json(cfg.CREDITS_FILE, list(credits.values()))

    write_json(cfg.DETAILS_FILE, list(details.values()))
    write_json(cfg.CREDITS_FILE, list(credits.values()))
    write_json(cfg.FAILED_FILE, [
        {"movie_id": int(k), "error": v} for k, v in failures.items()
    ])

    # ------------------------------------------------------------------
    # 3. LEDGER: one status for every input row
    # ------------------------------------------------------------------
    ids["status"] = "fetched"
    ids.loc[ids["tmdb_id"].isna(), "status"] = ids["id_kind"].map(
        {"missing": "dropped_missing_id",
         "invalid_number": "dropped_invalid_id",
         "unparseable": "dropped_unparseable_id",
         "imdb": "dropped_imdb_unresolved"})
    ids.loc[ids["is_duplicate"], "status"] = "dropped_duplicate"
    failed_ids = set(failures) | (
        set(ids["tmdb_id"].dropna().astype(int)) - set(details)
    )
    ids.loc[ids["tmdb_id"].isin(failed_ids) & ~ids["is_duplicate"],
            "status"] = "dropped_not_found_in_api"
    ids["note"] = ids.apply(
        lambda r: "imdb id resolved to tmdb" if r["id_kind"] == "imdb"
        and pd.notna(r["tmdb_id"]) else "", axis=1)
    ids.to_csv(cfg.LEDGER_FILE, index=False)

    summary = ids["status"].value_counts()
    assert summary.sum() == len(ids), "Ledger does not reconcile to input rows"

    print("\n" + "=" * 45)
    print("LEDGER (every input row accounted for)")
    print(summary.to_string())
    print(f"Total input rows: {len(ids)}")
    print(f"Elapsed: {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()