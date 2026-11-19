# Data findings — StreamVault (Kwame Boateng)

## Summary

The 127-row candidate list produced **112 usable films (93% of the 120 distinct rows)**. The films that did arrive are clean: no missing money fields, no unreleased titles, no join breaks. The risk is not in the fetched data. It is in what the data is and how the question is defined.

Three things move the recommendation, in order:

1. **What "better" means.** On an equal mix of return, revenue and rating, bundles and standalones are statistically tied in both windows. On revenue alone bundles win clearly; on rating alone standalones win clearly.
2. **The list is all hits.** Every film has at least 4,137 votes and earned at least 1.13 times its budget. The comparison is "hit bundle vs hit standalone", not "bundle vs the market".
3. **Pre-2000 films carry the standalone side.** 13 of 25 standalones (52%) are pre-2000, against 28 of 87 franchise films (32%). All five top standalones in the all-years view are pre-2000.

**The two windows do not give the same story.** Both are inconclusive on the average, but the typical (median) film flips: all years, the typical standalone beats the typical franchise film (+0.16 vs -0.06); from 2000 on, the typical franchise film beats the typical standalone (+0.05 vs -0.54).

## Reconciliation

| Stage | Rows | Delta | Reason |
|---|---|---|---|
| Rows in id_list.csv | 127 | | As supplied |
| Repeated ids | 120 | -7 | 6 repeated numeric ids and 1 IMDb-format id (`tt0468569`) that is The Dark Knight again (id 155 appears 3 times) |
| Blank id | 119 | -1 | Empty row |
| Text "N/A" instead of an id | 118 | -1 | Not a number |
| Negative id (-1) | 117 | -1 | Not a valid film id |
| Not found by the source | 112 | -5 | Ids 8471293, 8471294, 9412887, 9412888, 7733901 return "not found" |
| Unusable money or date | 112 | 0 | None failed the checks |
| **Films in final analysis** | **112** | | 87 franchise, 25 standalone (all years); 56 and 15 from 2000 on |

Gap to Kwame: 8 candidate slots (6.7% of distinct rows) are unknown films. If they are blockbusters like the rest, the effect is small. If they are weak titles, the list is flattering the picture. This cannot be checked.

## Findings, ranked by risk

### F-01: The answer depends on how "better" is defined — Severity: High

- **What it is:** A film's value was never defined in the brief. I used an equal mix of return on budget, revenue (adjusted for inflation) and audience rating.
- **How I detected it:** Re-ran the comparison using each measure alone.
- **Scale:** Gap in favour of franchise (score units; interval in brackets):

| Measure | All years | 2000-onward |
|---|---|---|
| Equal mix (my choice) | +0.04 (-0.32, +0.41) tied | +0.39 (-0.04, +0.85) tied |
| Return on budget only | +0.08 tied | +0.47 tied |
| Revenue only | +1.05 franchise wins | +1.10 franchise wins |
| Rating only | -1.00 standalone wins | -0.42 tied |

- **Effect on the client's number:** This is the whole recommendation. A negotiator who says "bundles earn more" and one who says "standalones are better loved" are both right.
- **What I did about it:** Reported the equal-mix result as the headline and stated it as an assumption.
- **Residual risk:** If Kwame's board cares about revenue alone, the answer is franchise.

### F-02: The candidate list contains only proven hits — Severity: High

- **What it is:** The list was assembled from tracking sheets and a studio email, so it holds films someone already thought worth evaluating.
- **How I detected it:** Distribution check: lowest vote count 4,137, lowest revenue $7.4M, lowest return 1.13x, no film below its budget, no unreleased title.
- **Scale:** 112 of 112 films.
- **Effect on the client's number:** Franchise "weak middle entries" are barely visible here, because even the weak entries are successful. Kwame's team argues the weak middle is the risk. This data cannot test that fully.
- **What I did about it:** Measured the weak-entry share anyway (62% of franchise films fall below the typical standalone all years; 21% from 2000 on) and flagged it.
- **Residual risk:** High. The real risk, a flop inside a bundle, is mostly absent from the data.

### F-03: Pre-2000 films carry the standalone side — Severity: High

- **What it is:** 41 of 112 films (37%) are pre-2000, and they are unevenly split: 13 of the 25 standalones, 28 of the 87 franchise films.
- **How I detected it:** Release-year split by segment.
- **Scale:** The top five standalones all years are Jaws (1975), Lion King, Forrest Gump, Pulp Fiction (1994) and Schindler's List (1993). None survives Yaw's filter.
- **Effect on the client's number:** The all-years standalone shortlist rests entirely on films Finance distrusts. The 2000-onward standalone sample is only 15 films.
- **What I did about it:** Ran both windows side by side. Adjusted money to 2024 dollars, which barely changes the verdict (+0.04 vs +0.05 unadjusted).
- **Residual risk:** Medium. Yaw's objection is not only inflation (how box office was reported then), and I cannot correct for that.

### F-04: "Franchise" is defined by the list, not by the studio's bundle — Severity: Medium-High

- **What it is:** A bundle means all films in a series. I can only see the films in the candidate list. Star Wars has 6 films in the list, and the source's own collection may be larger.
- **How I detected it:** Counted films per collection in the list; 9 collections have only one film.
- **Scale:** 9 films sit in a one-film collection (e.g. Jaws, The Lion King, Blade Runner). 16 have no collection at all.
- **Effect on the client's number:** The 2000-onward result moves with the definition: counting one-film collections as franchise gives +0.26 (tied); requiring 3+ films gives +0.47 (franchise wins, interval +0.13 to +0.84). All years stays tied in every version.
- **What I did about it:** Rule: franchise = 2+ films in the list; everything else is standalone. Both groups are named in the output.
- **Residual risk:** Medium-High. Bundle price and bundle size are not in the data.

### F-05: Repeated ids, one hidden in another format — Severity: Medium

- **What it is:** 7 rows repeat an earlier film. One (`tt0468569`) is an IMDb id, so a numeric check would miss it. It is The Dark Knight, already listed twice.
- **How I detected it:** Classified each id by format before converting; looked up the IMDb id.
- **Scale:** 7 of 127 rows (5.5%). Not removing them would add 3 standalone rows (Pulp Fiction, Shawshank, Fight Club) and 4 franchise rows.
- **Effect on the client's number:** Double-counted films would weight hit films twice, and make The Dark Knight and Matrix collections look larger.
- **What I did about it:** Kept first occurrence, logged every removal in the id ledger.
- **Residual risk:** Low.

### F-06: Eight candidate slots could not be recovered — Severity: Medium

- **What it is:** 1 blank, 1 "N/A", 1 "-1", 5 ids the source does not know.
- **How I detected it:** Id classification plus the source's "not found" replies.
- **Scale:** 8 of 120 distinct rows (6.7%).
- **Effect on the client's number:** Unknown. The five ids sit far outside the source's normal range and come in consecutive pairs, so they look like entry errors, not real films.
- **What I did about it:** Listed them in the ledger and in the failed-films file.
- **Residual risk:** Medium. Someone who owns the three source sheets should confirm.

### F-07: Inflation table was typed in, not downloaded — Severity: Low

- **What it is:** The price index used for adjusting revenue was entered from memory; the latest years are estimates.
- **How I detected it:** Self-review.
- **Scale:** All 112 films, but the verdict is unchanged without it (+0.04 vs +0.05; +0.39 vs +0.38).
- **Effect on the client's number:** Negligible for the headline. It could shift individual shortlist positions.
- **What I did about it:** Kept it in one settings file for replacement.
- **Residual risk:** Low.

## Looked wrong, is not wrong

| Apparent problem | Why it looks wrong | Why it is actually fine |
|---|---|---|
| Revenue many times the budget (up to 70x) | Looks like a unit error | Plausible for hit films; no film has revenue under budget or zero money |
| 16 films with no collection | Looks like missing data | They are genuine standalones (Inception, Fight Club, Schindler's List) |
| 9 films in a one-film collection | Looks like a broken series | The source tags a series even if only one film is in our list; treated as standalone |
| Two names for one director (Russo brothers) | Looks like a duplicate | Co-directed; both credited, 9 films have more than one director |
| Hobbit and Lord of the Rings are separate bundles; Avengers and Iron Man too | Look like one series | The source keeps them as separate collections, matching how studios sell them |
| 2 non-English films (Spirited Away, The Good, the Bad and the Ugly) | Look off-market | Valid candidates; both released and with full money data |
| One crew member without a department | Looks like missing data | Does not touch directors or cast, which are the only credits used |
| Rating column barely varies | Looks like a weak signal | Normal for films with 4,000+ votes each |

## Could not verify

- **Money figures.** Budget and revenue come from a crowd-edited public source, in nominal dollars, and are not audited. Revenue is assumed to be worldwide gross. A wrong figure on a few titles could move a franchise rank.
- **What the studio is asking.** No licence price, bundle size or term is in the data, so "what to pay" can only be stated relative to other titles, not in dollars.
- **Whether each series is complete in the list.** Checking needs the source's full series lists.
- **Which of the three source sheets each row came from.** The list carries no source label, so the eight lost rows cannot be traced to a person.
- **How these films performed on a streaming service.** Everything here is cinema performance. Streaming viewing could differ.
