# StreamVault: Back-Catalog Licensing Analysis

Pulls film data from the TMDb API for a licensing candidate list, cleans it, and compares **franchise bundles vs standalone hits** (all years and 2000-onward), with a shortlist and a talent signal.

## Folder layout

```
StreamVault/
├── .env                  API_READ_ACCESS_TOKEN=<your TMDb read token>
├── CVS_DATA/id_list.csv  candidate list (input)
├── data/raw/             API responses + failed_movies.json   (extract)
├── data/processed/       id_ledger, movies_clean, quality & reconciliation reports (transform)
├── Data_transform/       config.py  utils.py  api_fetch.py  extract.py  transform.py  analysis.py
├── Data_profiling/       profile_data.ipynb   (JSON -> DataFrames + profiling)
└── outputs/              shortlists, talent tables, segment comparison, verdicts
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Put your TMDb read token in `.env` at the project root.

## Run (from `Data_transform`)

```
python extract.py     # fetch, resumable; writes the id ledger
python transform.py   # flatten, validate, reconcile
python analysis.py    # two-window comparison, shortlist, talent, deal-note numbers
```

Optional: open `Data_profiling/profile_data.ipynb` for the analyst view of the raw data.

## How it works

- **extract**: every input row gets a status (fetched / duplicate / invalid / missing / not found). Re-runs skip films already stored, so a 500-title list resumes after a failure.
- **transform**: nested JSON becomes flat tables; joins are asserted 1:1; every film is flagged for data problems; money is adjusted to 2024 dollars.
- **analysis**: franchise = a collection with 2+ films in the list; **everything else is standalone**. Score = equal mix of return on budget, inflation-adjusted revenue and rating. Gap between segments is tested with a bootstrap interval.

## Change a decision

All thresholds (cutoff year, minimum bundle size, lead-cast size, CPI table) are in `Data_transform/config.py`.

## Known limits

See `data_findings.md`. Short version: the list contains only proven hits, TMDb money is unaudited, and the segment verdict depends on how "better" is defined.
