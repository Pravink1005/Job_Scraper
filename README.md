# Unified Job Scraping & Pipeline System

A single project that merges two previously separate repositories:

- **[LinkedIn_Job_Pipeline](https://github.com/Pravink1005/LinkedIn_Job_Pipeline)** — scrapes recent LinkedIn postings with [Scrapling](https://github.com/D4Vinci/Scrapling) (requests-style fetching, with an optional stealth/headless-browser mode) and uses trained TF-IDF + Logistic Regression models to predict required degree and specialization.
- **[Naukri-scraper](https://github.com/Pravink1005/Naukri-scraper)** — scrapes recent Naukri.com postings with [Playwright](https://playwright.dev/python/) (a real controlled browser, needed because Naukri's pages are JS-rendered and bot-protected).

Both scrapers keep their original scraping technology and parsing logic unchanged. What's new is the layer that sits on top of them: a **unified data schema**, a **shared normalization + enrichment + storage pipeline**, **error isolation** between sources, and a **combined test suite and CLI**.

> **Use responsibly.** Both source projects include their own reminders to respect the target sites' `robots.txt` and Terms of Use, and to scrape at a reasonable rate. Those reminders are preserved here — see [Notes on scraping etiquette](#notes-on-scraping-etiquette) below.

---

## Project structure

```text
job_scraper_pipeline/
├── main.py                      CLI entry point for the unified pipeline
├── config.py                    Central, environment-driven configuration
├── requirements.txt             Consolidated dependencies for both scrapers + pipeline
├── .env.example                 Copy to .env to override any setting
├── pytest.ini
│
├── scrapers/
│   ├── linkedin/
│   │   └── scraper.py           Original Main.py logic, refactored into collect_linkedin_jobs()
│   └── naukri/
│       └── scraper.py           Original naukri_scraper.py logic, refactored into collect_naukri_jobs()
│
├── ml/                          Shared ML assets (single source of truth — no duplicates)
│   ├── ml_predictor.py          Skill/experience extraction + degree/specialization prediction
│   ├── train_models.py          Retrains the two classifiers
│   ├── Degree_Prediction_Training_5000_Corrected.csv   Training data
│   └── models/                  Saved *.pkl vectorizers/classifiers
│
├── pipeline/
│   ├── schema.py                UnifiedJob — the one data model both sources normalize into
│   ├── normalizer.py            normalize_linkedin_job() / normalize_naukri_job()
│   ├── enrichment.py            Shared ML back-fill step (mainly benefits Naukri)
│   ├── storage.py               Unified CSV export + cross-run dedup state
│   ├── orchestrator.py          run_pipeline(): scrape -> normalize -> enrich -> dedupe -> store
│   └── errors.py                ScraperError / DataValidationError / StorageError
│
├── tests/                       76 unit tests covering both scrapers' pure logic,
│                                 the normalizer, storage, enrichment, and orchestrator error paths
│
└── csv_output/                  unified_jobs.csv + seen_job_ids.json land here by default
```

## How the two projects were combined

| Concern | LinkedIn_Job_Pipeline (before) | Naukri-scraper (before) | Unified system (now) |
|---|---|---|---|
| Scraping tech | Scrapling (`Fetcher` / `StealthyFetcher`) | Playwright (Chromium/Firefox) | **Unchanged per source** — each keeps its own tech in `scrapers/<source>/scraper.py` |
| Data shape | `job_id, category, title, company, city, state, country, ...` | `url, title, company, location, experience, salary, ...` | **`UnifiedJob`** (`pipeline/schema.py`) — one schema, one CSV |
| Degree/Specialization | ML-predicted at scrape time (`ml_predictor.py`) | Regex-extracted "Education" text only, no ML | ML models are now **shared** (`ml/`) and used as a **back-fill enrichment step** (`pipeline/enrichment.py`) for whichever source didn't already produce a confident value |
| Storage/dedup | `csv_output/current_jobs.csv` + `seen_job_ids.json` | Fresh CSV per run, no cross-run dedup | One `JobStore` (`pipeline/storage.py`) used by both, keyed by source-prefixed `job_id` (`linkedin_...` / `naukri_...`) so there's no collision risk |
| Error handling | `try/except` around fetches; no error taxonomy | `try/except` around page loads; no error taxonomy | Custom `ScraperError` / `DataValidationError` / `StorageError` (`pipeline/errors.py`); the orchestrator isolates failures **per source**, so a LinkedIn outage never stops Naukri from running (and vice versa) |
| Running | `python Main.py` (LinkedIn only) | `python naukri_scraper.py ...` (Naukri only) | `python main.py --source both\|linkedin\|naukri` |

Both original standalone scripts still work as scripts too — `python scrapers/linkedin/scraper.py` and `python scrapers/naukri/scraper.py` behave like the originals — but the recommended way to run the combined system is `main.py`.

---

## Setup

### 1. Requirements

- Python 3.10+
- Internet access for scraping (LinkedIn and/or Naukri)

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Naukri's scraper needs a real browser binary:
playwright install chromium
```

The saved degree/specialization models were trained with **scikit-learn 1.6.1**; that exact version is pinned in `requirements.txt` to avoid the model-compatibility warnings scikit-learn prints when unpickling artifacts from a different version. If you retrain with a newer scikit-learn, update the pin to match.

### 3. Configure (optional)

```bash
cp .env.example .env
```

Edit `.env` to change search keywords/titles, locations, page limits, headless mode, etc. Every value also has a CLI override (see below) and a hard-coded default in `config.py` matching each original project's defaults.

---

## Running the combined system

```bash
# Scrape both sources in one run (default)
python main.py

# Just one source
python main.py --source linkedin
python main.py --source naukri

# Override search terms without touching .env
python main.py --source linkedin --linkedin-keywords "Data Engineer,ETL Developer" --linkedin-location "India"
python main.py --source naukri --naukri-titles "data analyst,business analyst" --naukri-max-pages 3

# Watch Naukri's browser instead of running headless (useful when debugging CAPTCHAs)
python main.py --source naukri --naukri-headless=false
```

Every run prints a summary like:

```text
[Pipeline] Starting run for source='both' -> output=csv_output

[Pipeline] Run summary:
  LinkedIn: collected=42, normalized=41, skipped_invalid=1
  Naukri: collected=18, normalized=18, skipped_invalid=0
  New rows written to unified CSV: 55
```

- **collected** — raw records the scraper returned
- **normalized** — records that passed validation and became `UnifiedJob`s
- **skipped_invalid** — records missing a required field (title/link), logged and dropped rather than crashing the run
- **New rows written** — after cross-run deduplication against `seen_job_ids.json`

Output lands in:

```text
csv_output/unified_jobs.csv       # one combined table for both sources
csv_output/seen_job_ids.json      # dedup state, shared across sources and runs
```

`unified_jobs.csv` columns: `job_id, source, title, company, category, city, state, country, min_experience_years, max_experience_years, salary, skills, degree_required, specialization_required, posted_time, collected_at, link, full_description`.

### Running the scrapers standalone

If you only want one scraper with none of the pipeline/enrichment layer, the original entry points still exist:

```bash
python scrapers/linkedin/scraper.py     # prints "Collected N LinkedIn jobs."
python scrapers/naukri/scraper.py       # writes naukri_extracted_jobs.csv, like the original CLI
```

### Retraining the ML models

```bash
python ml/train_models.py
```

Reads `ml/Degree_Prediction_Training_5000_Corrected.csv`, retrains both classifiers, and overwrites the four `.pkl` files in `ml/models/`.

---

## Configuration reference

All variables below can be set in `.env` (see `.env.example`) or as real environment variables; CLI flags on `main.py` take precedence over both.

| Variable | Default | Meaning |
|---|---|---|
| `PIPELINE_OUTPUT_DIR` | `csv_output` | Where the unified CSV + dedup state are written |
| `LINKEDIN_KEYWORDS` | `Python Full Stack Developer,Python Backend Developer,SQL Developer` | Comma-separated search terms |
| `LINKEDIN_LOCATION` | `India` | LinkedIn location filter |
| `LINKEDIN_MAX_JOBS_PER_KEYWORD` | `100` | Cap per keyword |
| `LINKEDIN_JOBS_PER_PAGE` | `25` | LinkedIn's page size |
| `LINKEDIN_MAX_AGE_HOURS` | `1` | Only keep postings at most this many hours old |
| `NAUKRI_JOB_TITLES` | `data analyst` | Comma-separated job titles (converted to Naukri URL slugs) |
| `NAUKRI_MAX_PAGES` | `5` | Max search-result pages crawled per title |
| `NAUKRI_MAX_JOBS` | `100` | Max job links collected per title |
| `NAUKRI_MAX_TOTAL` | *(none)* | Optional cap across all titles combined |
| `NAUKRI_DELAY_SECONDS` | `2.0` | Delay between Naukri requests — **do not set to 0**, this is what keeps the scraper polite |
| `NAUKRI_HEADLESS` | `true` | Run Naukri's browser headless |
| `NAUKRI_BROWSER` | `chromium` | `chromium` or `firefox` |
| `NAUKRI_PROFILE_DIR` | *(none)* | Persistent browser profile directory, useful for manually solving a CAPTCHA once and reusing the session |

---

## Testing

```bash
pip install -r requirements.txt   # includes pytest
pytest
```

The suite (76 tests) is deliberately network-free — every scraping helper that doesn't require a live page is tested directly, and the two Playwright/Scrapling-dependent I/O calls (`safe_fetch_get`, `scrape_job_detail`/`get_job_links`) are exercised indirectly through the orchestrator using fake collector functions, so `pytest` runs without needing Playwright browsers installed or network access.

| File | Covers |
|---|---|
| `tests/test_schema.py` | `UnifiedJob` defaults, CSV row shape |
| `tests/test_normalizer.py` | Both sources' happy paths, missing-field validation errors, experience/date parsing edge cases |
| `tests/test_storage.py` | CSV append/header behavior, dedup state persistence, corrupt-state recovery |
| `tests/test_orchestrator_errors.py` | Per-source failure isolation, invalid-record skipping, dedup across runs, total-failure vs. partial-failure behavior |
| `tests/test_enrichment.py` | ML back-fill only applies when a field is genuinely unset |
| `tests/test_linkedin_helpers.py` | URL/job-ID canonicalization, relative/absolute posted-time parsing |
| `tests/test_naukri_helpers.py` | Slug/URL building, pagination URL building, posted-date parsing (including the "11/21/31 days" regression this project's original code specifically guards against), company/skill/education text cleaning |

To verify every module still compiles cleanly (a quick smoke check independent of pytest):

```bash
python -m py_compile main.py config.py $(find pipeline scrapers ml -name '*.py')
```

---

## Error handling design

- **`ScraperError`** — raised when a source can't produce *any* data (e.g. every LinkedIn search request fails, or Naukri's Playwright browser can't launch, or Naukri is blocked on every search URL). The orchestrator catches this **per source** and continues with the other source; the CLI only exits non-zero if *every* requested source failed.
- **`DataValidationError`** — raised by the normalizer for a single record missing a required field (`title` or `link`/`url`). The orchestrator catches this **per record**, logs it, and continues normalizing the rest of the batch — one malformed job card never aborts a run.
- **`StorageError`** — raised if the CSV or dedup-state file can't be written (e.g. permissions, disk full).
- Anything else unexpected (a genuine bug) is still caught at the per-source level in the orchestrator and reported in the run summary rather than crashing the whole pipeline outright, though it's logged clearly as "unexpected error" so it's not confused with an ordinary scraping hiccup.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ScraperError: [Naukri] Playwright is not installed` | Run `pip install -r requirements.txt` then `playwright install chromium` |
| Naukri run logs "Access Denied" / verification page | Naukri is showing a CAPTCHA or bot-check. Re-run with `--naukri-headless=false` and a `NAUKRI_PROFILE_DIR` set, solve the check once in the visible browser, then subsequent runs reuse that session |
| LinkedIn run collects 0 jobs but doesn't error | LinkedIn's search HTML structure changed, or `LINKEDIN_MAX_AGE_HOURS` is too strict for current listings — try increasing it |
| `InconsistentVersionWarning` from scikit-learn on startup | Cosmetic — it means your installed scikit-learn differs from the version (`1.6.1`) the shipped `.pkl` models were trained with. Either install `scikit-learn==1.6.1` (already pinned in `requirements.txt`) or run `python ml/train_models.py` to retrain with your installed version |
| `[ML Models Error] Failed to load models` | The `.pkl` files under `ml/models/` are missing or corrupted — retrain with `python ml/train_models.py`, which needs `ml/Degree_Prediction_Training_5000_Corrected.csv` to be present |
| Duplicate jobs keep reappearing across runs | Confirm `csv_output/seen_job_ids.json` (or your `PIPELINE_OUTPUT_DIR`) is writable and not being deleted between runs |
| Pipeline exits with status 1 | Every requested source failed outright this run — check the printed summary for the specific `ScraperError` message per source |

## Notes on scraping etiquette

Carried over unchanged from the original projects:

- Naukri's scraper includes deliberate delays between requests (`NAUKRI_DELAY_SECONDS`, default 2s) specifically to avoid rate-limiting/blocks — don't remove or zero these out.
- Both target sites can change their HTML structure or block scraping at any time; selectors here may need updating if either site changes its markup.
- This project is intended for personal/research use. Review `robots.txt` and the Terms of Use of LinkedIn and Naukri before scraping at scale or for commercial purposes.
