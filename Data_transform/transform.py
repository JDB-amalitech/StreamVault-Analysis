"""
Transform: raw nested JSON -> tidy, validated, analysis-ready tables.

Outputs (data/processed):
  movies_clean.csv   one row per film that enters the analysis
  talent_long.csv    one row per (film, role, person): director / lead
  quality_report.csv every data problem found and how many films it touches
  reconciliation.csv input rows -> final analysis, step by step
"""
import time

import numpy as np
import pandas as pd

import config as cfg
from utils import read_json


def build_movies(details):
    keep = [
        "id", "title", "imdb_id", "release_date", "status", "adult",
        "budget", "revenue", "runtime", "vote_average", "vote_count",
        "popularity", "original_language",
        "belongs_to_collection.id", "belongs_to_collection.name",
    ]
    df = pd.json_normalize(details)
    for col in keep:                       # tolerate missing keys
        if col not in df.columns:
            df[col] = np.nan
    df = df[keep].rename(columns={
        "belongs_to_collection.id": "collection_id",
        "belongs_to_collection.name": "collection_name",
    })
    df["collection_id"] = df["collection_id"].astype("Int64")
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"] = df["release_date"].dt.year.astype("Int64")
    return df


def build_talent(credits, movie_ids):
    """Directors and lead actors without Python row loops."""
    crew = pd.json_normalize(credits, record_path="crew", meta=["id"],
                             meta_prefix="movie_", errors="ignore")
    directors = crew.loc[crew["job"] == "Director",
                         ["movie_id", "id", "name"]].copy()
    directors["role"] = "director"

    cast = pd.json_normalize(credits, record_path="cast", meta=["id"],
                             meta_prefix="movie_", errors="ignore")
    leads = cast.loc[cast["order"] < cfg.LEAD_CAST_SIZE,
                     ["movie_id", "id", "name"]].copy()
    leads["role"] = "lead_actor"

    talent = pd.concat([directors, leads], ignore_index=True)
    talent = talent.rename(columns={"id": "person_id", "name": "person_name",
                                    "movie_id": "id"})
    talent = talent[talent["id"].isin(movie_ids)]
    return talent.drop_duplicates(["id", "role", "person_id"])


def add_quality_flags(df):
    """Flag, don't silently fix. Each flag is a documented problem."""
    df["flag_zero_budget"] = df["budget"].fillna(0).eq(0)
    df["flag_zero_revenue"] = df["revenue"].fillna(0).eq(0)
    df["flag_implausible_budget"] = (
        df["budget"].between(1, cfg.MIN_PLAUSIBLE_BUDGET - 1))
    df["flag_revenue_below_budget"] = df["revenue"].lt(df["budget"]) & \
        ~df["flag_zero_revenue"]
    df["flag_not_released"] = df["status"].ne("Released")
    df["flag_missing_date"] = df["release_date"].isna()
    df["flag_zero_runtime"] = df["runtime"].fillna(0).eq(0)
    df["flag_low_votes"] = df["vote_count"].fillna(0).lt(100)
    df["flag_missing_cpi"] = ~df["release_year"].isin(list(cfg.CPI_US))
    df["flag_dup_imdb"] = df["imdb_id"].notna() & \
        df.duplicated("imdb_id", keep=False)
    df["flag_pre_cutoff"] = df["release_year"].lt(cfg.CUTOFF_YEAR)

    exclude = (df["flag_zero_budget"] | df["flag_zero_revenue"]
               | df["flag_implausible_budget"] | df["flag_not_released"]
               | df["flag_missing_date"] | df["flag_missing_cpi"])
    df["excluded"] = exclude
    return df


def add_money_columns(df):
    """Inflation-adjust to base-year dollars; compute ROI."""
    cpi = df["release_year"].map(cfg.CPI_US).astype(float)
    factor = cfg.CPI_US[cfg.CPI_BASE_YEAR] / cpi
    df["inflation_factor"] = factor
    df["budget_real"] = df["budget"] * factor
    df["revenue_real"] = df["revenue"] * factor
    df["roi"] = df["revenue"] / df["budget"]       # unit-free, era-neutral
    df["log_roi"] = np.log(df["roi"])
    df["log_revenue_real"] = np.log(df["revenue_real"])
    # Bayesian rating: shrinks low-vote titles toward the pool average
    m = cfg.RATING_PRIOR_VOTES
    pool_avg = df["vote_average"].mean()
    v = df["vote_count"]
    df["rating_adj"] = (v * df["vote_average"] + m * pool_avg) / (v + m)
    return df


def assign_franchise(df):
    """
    Franchise = TMDb collection with >= MIN_FRANCHISE_SIZE films in the
    clean candidate list. Everything else is a standalone.
    """
    size = df.groupby("collection_id")["id"].transform("size")
    df["collection_size_in_list"] = size.fillna(0).astype(int)
    df["segment"] = np.where(
        df["collection_id"].notna() & (size >= cfg.MIN_FRANCHISE_SIZE),
        "franchise", "standalone")
    return df


def main():
    start = time.perf_counter()
    details = read_json(cfg.DETAILS_FILE)
    credits = read_json(cfg.CREDITS_FILE)
    ledger = pd.read_csv(cfg.LEDGER_FILE)

    movies = build_movies(details)

    # ---- JOIN INTEGRITY: details and credits must match 1:1 ----------
    assert movies["id"].is_unique, "Duplicate film ids in details"
    credit_ids = pd.Series([c["id"] for c in credits])
    assert credit_ids.is_unique, "Duplicate film ids in credits"
    assert set(movies["id"]) == set(credit_ids), "details/credits id mismatch"

    talent = build_talent(credits, set(movies["id"]))
    n_before = len(movies)
    movies = add_quality_flags(movies)
    movies = add_money_columns(movies.assign(
        vote_average=movies["vote_average"].astype(float)))
    movies = assign_franchise(movies)
    assert len(movies) == n_before, "A transform step changed the film count"

    # one director column for the analysis (first director if co-directed)
    first_dir = (talent[talent["role"] == "director"]
                 .drop_duplicates("id")[["id", "person_name"]]
                 .rename(columns={"person_name": "director"}))
    merged = movies.merge(first_dir, on="id", how="left", validate="1:1")
    assert len(merged) == len(movies), "Director join dropped/duplicated films"
    movies = merged

    # ---- QUALITY REPORT (ranked by films touched) --------------------
    flag_cols = [c for c in movies.columns if c.startswith("flag_")]
    report = (movies[flag_cols].sum().rename("films_affected")
              .rename_axis("problem").reset_index()
              .sort_values("films_affected", ascending=False))
    report["share_of_films"] = (report["films_affected"] / len(movies)).round(3)
    id_problems = (ledger.loc[ledger["status"] != "fetched", "status"]
                   .value_counts().rename_axis("problem")
                   .reset_index(name="films_affected"))
    id_problems["share_of_films"] = np.nan
    report = pd.concat([id_problems, report], ignore_index=True)
    report.to_csv(cfg.PROCESSED_DIR / "quality_report.csv", index=False)

    # ---- RECONCILIATION: input rows -> analysis ----------------------
    clean = movies.loc[~movies["excluded"]].copy()
    steps = ledger["status"].value_counts().to_dict()
    recon = pd.DataFrame([
        {"step": "input rows in id_list.csv", "rows": len(ledger)},
        *[{"step": f"  lost: {k}", "rows": -v}
          for k, v in steps.items() if k != "fetched"],
        {"step": "films fetched (details+credits)", "rows": len(movies)},
        {"step": "  lost: excluded for unusable financials/dates",
         "rows": -int(movies["excluded"].sum())},
        {"step": "films in final analysis", "rows": len(clean)},
    ])
    assert recon.loc[recon["step"].str.startswith("input"), "rows"].iloc[0] + \
        recon.loc[recon["step"].str.startswith("  lost"), "rows"].sum() == len(clean), \
        "Reconciliation does not add up"
    recon.to_csv(cfg.PROCESSED_DIR / "reconciliation.csv", index=False)

    clean.to_csv(cfg.PROCESSED_DIR / "movies_clean.csv", index=False)
    talent[talent["id"].isin(clean["id"])].to_csv(
        cfg.PROCESSED_DIR / "talent_long.csv", index=False)

    print("\nQUALITY REPORT\n", report.to_string(index=False))
    print("\nRECONCILIATION\n", recon.to_string(index=False))
    print(f"\nTransform elapsed: {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main()