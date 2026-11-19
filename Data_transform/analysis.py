"""
Analysis: franchise vs standalone (all years AND 2000-onward), shortlist,
talent signal, and the deal-note numbers. Fully vectorised.
Run:  python extract.py && python transform.py && python analysis.py
"""
import time

import numpy as np
import pandas as pd
import config as cfg

rng = np.random.default_rng(getattr(cfg, "RANDOM_SEED", 42))


# ------------------------------------------------------------------
# SCORE: era-neutral value of a film, z-scored inside each window
# ------------------------------------------------------------------
def z(s):
    return (s - s.mean()) / s.std(ddof=0)


def add_score(df):
    """Equal-weight mix of return on budget, real revenue and rating."""
    df = df.copy()
    df["score"] = (z(df["log_roi"]) + z(df["log_revenue_real"])
                   + z(df["rating_adj"])) / 3
    return df


# ------------------------------------------------------------------
# FRANCHISE vs STANDALONE
# ------------------------------------------------------------------
def bootstrap_gap(a, b):
    """95% interval for mean(a) - mean(b), vectorised."""
    ia = rng.integers(0, len(a), (cfg.N_BOOTSTRAP, len(a)))
    ib = rng.integers(0, len(b), (cfg.N_BOOTSTRAP, len(b)))
    gaps = a.to_numpy()[ia].mean(axis=1) - b.to_numpy()[ib].mean(axis=1)
    return np.percentile(gaps, [2.5, 97.5])


def compare_segments(df, label):
    df = add_score(df)
    seg = df.groupby("segment").agg(
        films=("id", "size"),
        mean_score=("score", "mean"),
        median_score=("score", "median"),
        mean_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        mean_rating=("vote_average", "mean"),
        median_real_revenue_m=("revenue_real", lambda s: s.median() / 1e6),
    ).round(3)
    seg["window"] = label

    fr = df.loc[df["segment"] == "franchise", "score"]
    st = df.loc[df["segment"] == "standalone", "score"]
    lo, hi = bootstrap_gap(fr, st)
    gap = fr.mean() - st.mean()

    # "weak middle entries": share of franchise films below the standalone median
    weak = (fr < st.median()).mean()

    if lo > 0:
        verdict = "FRANCHISE BUNDLES"
    elif hi < 0:
        verdict = "STANDALONE HITS"
    else:
        verdict = "NO CLEAR WINNER (gap within noise)"
    return df, seg, dict(window=label, gap=gap, ci_low=lo, ci_high=hi,
                         franchise_films_below_standalone_median=weak,
                         verdict=verdict)


# ------------------------------------------------------------------
# SHORTLIST
# ------------------------------------------------------------------
def top_franchises(df, n=3):
    g = df[df["segment"] == "franchise"].groupby(
        ["collection_id", "collection_name"]).agg(
        films=("id", "size"),
        mean_score=("score", "mean"),
        weakest_entry_score=("score", "min"),
        mean_roi=("roi", "mean"),
        weakest_entry_roi=("roi", "min"),
        mean_rating=("vote_average", "mean"),
        first_year=("release_year", "min"),
        last_year=("release_year", "max"),
    ).reset_index()
    # a bundle is all-or-none, so the weakest film counts against it
    g["bundle_value"] = 0.7 * g["mean_score"] + 0.3 * g["weakest_entry_score"]
    return g.sort_values("bundle_value", ascending=False).head(n).round(3)


def top_standalones(df, n=5):
    cols = ["id", "title", "release_year", "director", "roi",
            "vote_average", "revenue_real", "score"]
    return (df[df["segment"] == "standalone"]
            .sort_values("score", ascending=False)[cols].head(n).round(3))


# ------------------------------------------------------------------
# TALENT: who reliably signals a worthwhile title
# ------------------------------------------------------------------
def talent_table(df, talent, role):
    t = talent[talent["role"] == role].merge(
        df[["id", "score"]], on="id", how="inner", validate="m:1")
    hit_cut = df["score"].median()
    g = t.groupby(["person_id", "person_name"]).agg(
        films=("id", "nunique"),
        mean_score=("score", "mean"),
        hit_rate=("score", lambda s: (s > hit_cut).mean()),
    ).reset_index()
    g = g[g["films"] >= cfg.MIN_TALENT_FILMS].copy()
    pool_mean = df["score"].mean()
    # shrinkage: a 2-film average is weaker evidence than a 6-film one
    g["shrunk_score"] = (g["films"] * g["mean_score"]
                         + cfg.SHRINKAGE_K * pool_mean) / (g["films"] + cfg.SHRINKAGE_K)
    return g.sort_values("shrunk_score", ascending=False).head(10).round(3)


# ------------------------------------------------------------------
# DEAL NOTE
# ------------------------------------------------------------------
def deal_note(df, fr_table):
    top = fr_table.iloc[0]
    films = df[df["collection_id"] == top["collection_id"]]
    pool = df[df["segment"] == "standalone"]
    return {
        "franchise": top["collection_name"],
        "films_in_bundle": int(top["films"]),
        "bundle_mean_score": float(top["mean_score"]),
        "pool_mean_score": 0.0,   # scores are z-scored: pool mean = 0
        "weakest_entry": films.sort_values("score").iloc[0]["title"],
        "weakest_entry_score": float(top["weakest_entry_score"]),
        "bundle_mean_roi": float(top["mean_roi"]),
        "standalone_median_roi": float(pool["roi"].median()),
        "bundle_percentile_vs_standalones": float(
            (pool["score"] < top["mean_score"]).mean()),
    }


def main():
    start = time.perf_counter()
    movies = pd.read_csv(cfg.PROCESSED_DIR / "movies_clean.csv")
    talent = pd.read_csv(cfg.PROCESSED_DIR / "talent_long.csv")

    windows = {
        "all years": movies,
        f"{cfg.CUTOFF_YEAR}-onward": movies[movies["release_year"] >= cfg.CUTOFF_YEAR],
    }
    # segments are re-derived inside each window (a franchise needs >=2 films
    # IN that window, otherwise a bundle is not really on offer)
    results, verdicts, summaries = {}, [], []
    for label, frame in windows.items():
        frame = frame.copy()
        size = frame.groupby("collection_id")["id"].transform("size")
        frame["segment"] = np.where(
            frame["collection_id"].notna() & (size >= cfg.MIN_FRANCHISE_SIZE),
            "franchise", "standalone")
        scored, seg, verdict = compare_segments(frame, label)
        results[label] = scored
        summaries.append(seg.reset_index())
        verdicts.append(verdict)

    summary = pd.concat(summaries, ignore_index=True)
    verdict_df = pd.DataFrame(verdicts).round(3)
    summary.to_csv(cfg.OUTPUT_DIR / "segment_comparison.csv", index=False)
    verdict_df.to_csv(cfg.OUTPUT_DIR / "verdicts.csv", index=False)

    print("\n=== FRANCHISE vs STANDALONE ===")
    print(summary.to_string(index=False))
    print("\n", verdict_df.to_string(index=False))
    if verdict_df["verdict"].nunique() > 1:
        print("\n" + "!" * 60)
        print("!!! THE RECOMMENDATION CHANGES BETWEEN THE TWO WINDOWS !!!")
        print("!" * 60)

    for label, scored in results.items():
        print(f"\n=== SHORTLIST ({label}) ===")
        fr = top_franchises(scored)
        st = top_standalones(scored)
        print(fr.to_string(index=False))
        print(st.to_string(index=False))
        fr.to_csv(cfg.OUTPUT_DIR / f"top_franchises_{label.replace(' ', '_')}.csv", index=False)
        st.to_csv(cfg.OUTPUT_DIR / f"top_standalones_{label.replace(' ', '_')}.csv", index=False)

        for role in ("director", "lead_actor"):
            tt = talent_table(scored, talent, role)
            print(f"\n--- {role} ({label}) ---")
            print(tt.to_string(index=False))
            tt.to_csv(cfg.OUTPUT_DIR / f"talent_{role}_{label.replace(' ', '_')}.csv", index=False)

        print(f"\n--- DEAL NOTE NUMBERS ({label}) ---")
        for k, v in deal_note(scored, fr).items():
            print(f"{k}: {v}")

    print(f"\nAnalysis elapsed: {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main()