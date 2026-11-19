"""Central settings. Change a number here, not inside the pipeline code."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "CVS_DATA" / "id_list.csv"
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"

for _d in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DETAILS_FILE = RAW_DIR / "movie_details.json"
CREDITS_FILE = RAW_DIR / "movie_credits.json"
FAILED_FILE = RAW_DIR / "failed_movies.json"
LEDGER_FILE = PROCESSED_DIR / "id_ledger.csv"

# ---- Fetching ----------------------------------------------------------
MAX_WORKERS = 4            # polite concurrency for the TMDb API
SAVE_EVERY = 50            # checkpoint raw JSON every N fetched films

# ---- Analysis decisions (documented in the decision notes) ------------
CUTOFF_YEAR = 2000         # Yaw's window: films released in/after this year
MIN_FRANCHISE_SIZE = 2     # a "bundle" needs >= 2 candidate films
LEAD_CAST_SIZE = 3         # "lead actors" = top-billed cast (order 0..2)
MIN_TALENT_FILMS = 2       # director/actor needs >= 2 films to be rated
SHRINKAGE_K = 2            # pulls small-sample talent averages to the mean
RATING_PRIOR_VOTES = 5000  # Bayesian rating: weight of the pool average
MIN_PLAUSIBLE_BUDGET = 10_000   # below this a "budget" is a data error
N_BOOTSTRAP = 5000
RANDOM_SEED = 42

# ---- Inflation: US CPI-U annual averages (1982-84 = 100) ---------------
# ASSUMPTION: TMDb money is nominal USD. Replace with the official BLS
# series if you can; the pipeline only needs this year -> index mapping.
CPI_US = {
    1966: 32.5, 1967: 33.4, 1968: 34.8, 1969: 36.7, 1970: 38.8,
    1971: 40.5, 1972: 41.8, 1973: 44.4, 1974: 49.3, 1975: 53.8,
    1976: 56.9, 1977: 60.6, 1978: 65.2, 1979: 72.6, 1980: 82.4,
    1981: 90.9, 1982: 96.5, 1983: 99.6, 1984: 103.9, 1985: 107.6,
    1986: 109.6, 1987: 113.6, 1988: 118.3, 1989: 124.0, 1990: 130.7,
    1991: 136.2, 1992: 140.3, 1993: 144.5, 1994: 148.2, 1995: 152.4,
    1996: 156.9, 1997: 160.5, 1998: 163.0, 1999: 166.6, 2000: 172.2,
    2001: 177.1, 2002: 179.9, 2003: 184.0, 2004: 188.9, 2005: 195.3,
    2006: 201.6, 2007: 207.3, 2008: 215.3, 2009: 214.5, 2010: 218.1,
    2011: 224.9, 2012: 229.6, 2013: 233.0, 2014: 236.7, 2015: 237.0,
    2016: 240.0, 2017: 245.1, 2018: 251.1, 2019: 255.7, 2020: 258.8,
    2021: 271.0, 2022: 292.7, 2023: 304.7, 2024: 313.7, 2025: 322.0,
    2026: 330.0,
}
CPI_BASE_YEAR = 2024