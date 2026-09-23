Job Scraper Pipeline

A Python-based job scraping and data pipeline that collects job postings from LinkedIn and Naukri, converts them into one unified schema, validates and normalizes the data, performs ML-based degree/specialization enrichment, removes duplicates, and stores the results in both CSV and SQLite.

Current project goal: maintain one searchable, structured job database while making job-search keywords easy to change from one place.

Table of Contents

Features

Architecture

Supported Sources

Output Schema

Project Structure

Requirements

Installation

Configuration

Changing Search Keywords

Environment Configuration

Run the Pipeline

Command-Line Options

Important Run Examples

Run Tests

Data Quality Audit

SQLite Database

ML Enrichment

Deduplication

Data Flow

Typical Workflow

Troubleshooting

Development Notes

Responsible Scraping

License

Features

Job collection

LinkedIn job search scraping

Naukri job search scraping

Multiple search keywords

LinkedIn location filtering

Recent-job filtering for LinkedIn

Maximum-job controls

Optional Naukri detail-page enrichment

Data processing

Unified schema for both sources

Location normalization

Education normalization

Experience extraction

Missing-value handling with Not Specified

Job ID validation

URL validation

Duplicate removal

ML enrichment

The existing ML pipeline predicts/enriches:

degree_required

specialization_required

The ML enrichment step uses the project's existing models and rule-based logic.

Storage

unified_jobs.csv for portable tabular data

jobs.db for SQLite queries and downstream applications

Quality control

The project includes an automated production data-quality audit that checks:

CSV structure

duplicate job IDs

required fields

source validity

location contamination

education contamination

experience validity

link validity

SQLite row counts

CSV ↔ SQLite consistency

Architecture

                    +------------------+
                    |   config.py      |
                    | Search keywords  |
                    +--------+---------+
                             |
                +------------+------------+
                |                         |
                v                         v
       +----------------+        +----------------+
       |    LinkedIn    |        |     Naukri     |
       |    scraper     |        |    scraper     |
       +-------+--------+        +--------+-------+
               |                          |
               +------------+-------------+
                            v
                    +---------------+
                    |  Normalizer   |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    |   Validator   |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    | ML Enrichment |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    | Deduplication |
                    +-------+-------+
                            |
                   +--------+---------+
                   |                  |
                   v                  v
          unified_jobs.csv         jobs.db

Supported Sources

LinkedIn

The LinkedIn scraper supports:

multiple keywords

location

maximum jobs per keyword

maximum job age in hours

search-page extraction

detail-page extraction

ML enrichment

The current pipeline uses the LinkedIn detail page to obtain richer job-description information when detail enrichment is enabled.

Naukri

The Naukri scraper supports:

multiple search URLs

multiple titles

multiple pages

maximum total jobs

maximum jobs

headless browser operation

optional detail-page enrichment

The current pipeline run shown in development uses Naukri search-page extraction with detail enrichment disabled from the main pipeline.

Output Schema

The unified dataset contains 18 columns:

Column

Description

job_id

Unique job identifier

source

Job source such as linkedin or naukri

title

Job title

company

Company name

category

Category field; current normalizer sets this to Not Specified

city

Normalized city

state

Normalized state

country

Country

min_experience_years

Minimum required experience

max_experience_years

Maximum required experience

salary

Salary field; current normalizer sets this to Not Specified

skills

Extracted skills

degree_required

Required degree / qualification

specialization_required

Required specialization

posted_time

Job posted date/time information

collected_at

Time when the pipeline collected the job

link

Original job URL

full_description

Full or extracted job description

Missing or unavailable values are represented using:

Not Specified

Project Structure

Job_Scraper/
│
├── main.py                         # Main pipeline entry point
├── config.py                       # Central configuration, especially keywords
├── database.py                     # CSV → SQLite synchronization
│
├── pipeline/
│   ├── __init__.py
│   ├── errors.py                   # Pipeline error definitions
│   ├── normalizer.py               # Data normalization
│   ├── schema.py                   # Unified schema / UnifiedJob
│   ├── storage.py                  # Storage helpers
│   ├── orchestrator.py             # Pipeline orchestration
│   ├── enrichment.py               # ML enrichment integration
│   ├── data_quality.py             # Data-quality tests and production audit
│   └── repair_existing_data.py     # Existing-data repair utility
│
├── scrapers/
│   ├── linkedin/
│   │   └── scraper.py
│   └── naukri/
│       └── scraper.py
│
├── ml/
│   ├── ml_predictor.py             # Existing prediction logic
│   ├── train_models.py             # Model training
│   ├── test_production_ml.py       # Production ML testing
│   ├── analyze_ml_predictions.py
│   ├── analyze_training_data.py
│   ├── analyze_production_similarity.py
│   ├── create_production_labeling_file.py
│   ├── prepare_production_review.py
│   ├── evaluate_production_accuracy.py
│   ├── production_labeling.csv
│   ├── production_review.csv
│   ├── production_review_labeled.csv
│   ├── production_degree_errors.csv
│   ├── production_specialization_errors.csv
│   └── models/
│       ├── degree_vectorizer.pkl
│       ├── degree_model.pkl
│       ├── specialization_vectorizer.pkl
│       └── specialization_model.pkl
│
├── tests/                          # Project tests
│
├── csv_output/
│   ├── unified_jobs.csv            # Generated job dataset
│   └── jobs.db                     # Generated SQLite database
│
├── .env                            # Local environment settings (do not commit secrets)
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation

Generated data such as csv_output/unified_jobs.csv, csv_output/jobs.db, virtual environments, caches, logs, and local secrets should normally be excluded from Git with .gitignore.

Requirements

Recommended environment:

Windows, Linux, or macOS

Python 3.10+

Git

Internet connection

A Python virtual environment

The project was developed and tested using a Windows PowerShell environment with a .venv virtual environment.

Installation

1. Clone the repository

git clone https://github.com/Pravink1005/Job_Scraper.git
cd Job_Scraper

2. Create a virtual environment

Windows PowerShell:

python -m venv .venv

Activate it:

.\.venv\Scripts\Activate.ps1

You should see:

(.venv) PS D:\Job_Scraper>

3. Upgrade pip

python -m pip install --upgrade pip

4. Install dependencies

pip install -r requirements.txt

5. Browser dependency (only when required)

If the installed scraping stack reports a missing Chromium/Playwright browser, run:

playwright install chromium

Configuration

The main configuration file is:

config.py

The project uses config.py as the preferred place to maintain the central search keywords.

Other runtime settings may be supplied through environment variables / .env depending on the project configuration.

Changing Search Keywords

The simplest way to change both LinkedIn and Naukri searches is to edit the single keyword list in config.py.

Example:

DEFAULT_SEARCH_KEYWORDS = [
    "data analyst",
    "python developer",
    "data scientist",
    "business analyst",
]

After changing the list, run the normal pipeline:

python main.py --source both

The same keyword list is then used to generate the source-specific searches.

Example

DEFAULT_SEARCH_KEYWORDS = [
    "data analyst",
    "Java developer",
]

Produces searches such as:

LinkedIn:
  data analyst
  Java developer

Naukri:
  data analyst
  Java developer

Important

Do not maintain a different keyword list in multiple places. The purpose of the current architecture is to keep search keywords centralized.

Environment Configuration

Keep secrets and machine-specific settings in .env rather than committing them to Git.

A typical configuration can contain settings such as:

PIPELINE_OUTPUT_DIR=csv_output
LINKEDIN_LOCATION=India
LINKEDIN_MAX_JOBS_PER_KEYWORD=100
LINKEDIN_JOBS_PER_PAGE=25
LINKEDIN_MAX_AGE_HOURS=1
NAUKRI_MAX_PAGES=5
NAUKRI_MAX_JOBS=100
NAUKRI_MAX_TOTAL=
NAUKRI_DELAY_SECONDS=2.0
NAUKRI_HEADLESS=true
NAUKRI_BROWSER=chromium
NAUKRI_PROFILE_DIR=

The exact variables supported by the current version of config.py are the source of truth.

Do not commit

Never commit private values such as:

API keys

cookies

browser profiles containing private session data

passwords

personal tokens

Use .gitignore for .env and other private/runtime files.

Run the Pipeline

The main command is:

python main.py --source both

This runs:

LinkedIn
  ↓
Naukri
  ↓
Normalization
  ↓
Validation
  ↓
ML enrichment
  ↓
Deduplication
  ↓
CSV
  ↓
SQLite

Command-Line Options

The main pipeline supports the following source-level options.

Source

--source linkedin
--source naukri
--source both

Output directory

--output-dir csv_output

Rebuild output

--rebuild-output

Use this carefully. A rebuild can recreate the output from the current run rather than preserving previous production rows.

Disable ML enrichment

--no-enrichment

LinkedIn

--linkedin-max-jobs 5
--linkedin-max-age-hours 1

Additional LinkedIn settings may be configured through config.py / environment settings.

Naukri

--naukri-max-pages 5
--naukri-max-jobs 20
--naukri-headless

Important Run Examples

LinkedIn only

python main.py --source linkedin

Naukri only

python main.py --source naukri

Both sources

python main.py --source both

Small LinkedIn test run

python main.py --source both --linkedin-max-jobs 2 --linkedin-max-age-hours 1

This is useful when testing a configuration change without collecting a large number of LinkedIn jobs.

Disable ML enrichment

python main.py --source both --no-enrichment

Rebuild output

python main.py --source both --rebuild-output

Only use --rebuild-output when you intentionally want to rebuild the current output dataset.

Run Tests

Main module tests

python main.py --test

A successful test should include checks such as:

[PASS] Boolean parser
[PASS] CSV argument parser
[PASS] Empty CSV values removed
[PASS] Naukri single URL generation
[PASS] Naukri multiple URL generation
[PASS] SEARCH_KEYWORDS loaded from config.py
[PASS] Argument defaults
[PASS] LinkedIn arguments
[PASS] Naukri arguments
[PASS] Output path construction

Data-quality module tests + production audit

python -m pipeline.data_quality

This command first tests the data-quality module and then audits the actual production CSV/SQLite data.

Data Quality Audit

Run:

python -m pipeline.data_quality

A healthy production dataset should show results similar to:

[PASS] CSV contains expected 18 columns
[PASS] Duplicate job_id: 0
[PASS] Missing job_id: 0
[PASS] Missing source: 0
[PASS] Missing title: 0
[PASS] Missing company: 0
[PASS] Missing link: 0
[PASS] Invalid source: 0
[PASS] Polluted city: 0
[PASS] Polluted state: 0
[PASS] Polluted country: 0
[PASS] Education regex contamination: 0
[PASS] Experience problems: 0
[PASS] Missing links: 0
[PASS] SQLite total rows: ...
[PASS] CSV jobs missing in SQLite: 0
[PASS] SQLite jobs missing in CSV: 0

The audit verifies that the two storage layers contain the same jobs and that the production records satisfy the project's validation rules.

SQLite Database

The generated database is:

csv_output/jobs.db

The main pipeline already performs a SQLite synchronization at the end of a normal run.

Therefore, you normally do not need to run database.py after every scrape.

Manually synchronize CSV → SQLite

Run:

python database.py

This imports/synchronizes:

csv_output/unified_jobs.csv
          ↓
      csv_output/jobs.db

When to run database.py

Useful cases include:

you manually edited the CSV

the SQLite database was deleted

the SQLite database needs to be rebuilt from the CSV

you need a manual CSV → SQLite synchronization

Normal workflow

python main.py ...

is usually enough because the pipeline already writes/syncs both outputs.

ML Enrichment

The ML components live under:

ml/

The production enrichment flow uses the existing ML predictor to populate:

D degree_required
D specialization_required

The enrichment layer is designed to avoid overwriting already valid values and to continue the pipeline if an individual prediction fails.

Existing model files

ml/models/degree_vectorizer.pkl
ml/models/degree_model.pkl
ml/models/specialization_vectorizer.pkl
ml/models/specialization_model.pkl

Train or evaluate models

Model-training/evaluation utilities are available in the ml/ directory, including:

python ml/train_models.py
python ml/test_production_ml.py

Use the scripts in that directory according to their current code and data requirements.

Deduplication

The pipeline performs deduplication before writing new rows to the unified dataset.

The job URL / job ID is the important identity information used by the unified pipeline.

Two jobs should not be merged simply because they have the same title and company if they have different job IDs/URLs. Different posting IDs can represent separate postings.

Data Flow

A typical job passes through these stages:

1. Collection

The source scraper extracts raw job information.

2. Normalization

The normalizer converts different source formats into the unified 18-column schema.

3. Validation

Required fields and structured values are checked.

4. ML enrichment

Missing degree/specialization information can be enriched using the project's ML/rule-based predictor.

5. Deduplication

Jobs already present in the production dataset are not written again.

6. CSV output

New unified rows are appended to:

csv_output/unified_jobs.csv

7. SQLite sync

The CSV is synchronized with:

csv_output/jobs.db

Typical Workflow

First-time setup

git clone https://github.com/Pravink1005/Job_Scraper.git
cd Job_Scraper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Configure keywords in config.py, then test:

python main.py --test

Run a small scrape:

python main.py --source both --linkedin-max-jobs 2 --linkedin-max-age-hours 1

Verify the data:

python -m pipeline.data_quality

Normal daily run

.\.venv\Scripts\Activate.ps1
python main.py --source both
python -m pipeline.data_quality

Changing the search scope

Edit DEFAULT_SEARCH_KEYWORDS in config.py.

Run python main.py --test.

Run the pipeline.

Run python -m pipeline.data_quality.

Troubleshooting

ModuleNotFoundError

Make sure the virtual environment is activated and dependencies are installed:

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Naukri TypeError: unexpected keyword argument

The Naukri collector currently supports the parameter names exposed by:

python -c "import inspect; from scrapers.naukri.scraper import collect_naukri_jobs; print(inspect.signature(collect_naukri_jobs))"

Use the exact signature from your installed code. Do not pass unsupported arguments such as legacy names from an older version.

LinkedIn returns many cards but only a small number are accepted

This can be normal. The scraper may reject jobs that are outside the configured freshness window or stop after reaching --linkedin-max-jobs for the current keyword.

Example:

--linkedin-max-jobs 2

means a maximum of two accepted jobs per keyword in the controlled run.

Deprecated Scrapling warning

You may see a warning similar to:

This logic is deprecated now ... Use Fetcher.configure() instead before fetching

If the request still returns HTTP 200 and job extraction succeeds, this warning does not by itself mean the pipeline failed. Upgrade/refactor the related fetch configuration only when intentionally updating the scraper dependency/code.

Naukri returns zero jobs

Check:

internet connection

whether Naukri is returning HTTP 200

whether the current HTML selectors still match the page

whether the site is temporarily blocking requests

whether headless mode works correctly

Run a controlled Naukri-only test:

python main.py --source naukri

CSV and SQLite row counts do not match

Run:

python -m pipeline.data_quality

If the database needs to be rebuilt from the CSV and you have confirmed that the CSV is the correct source of truth:

python database.py

Always keep a backup before destructive/rebuild operations.

Browser errors

Try:

playwright install chromium

and rerun the controlled test.

Development Notes

Centralized keyword design

The search architecture intentionally keeps the job-title search configuration in one place so you can add or remove titles without editing both source integrations.

Compatibility-first schema

The unified schema keeps category and salary columns even when the current normalizer sets them to Not Specified. This preserves CSV/SQLite compatibility while allowing future enrichment.

Normalized experience parsing

The normalizer handles common patterns such as:

2-5 years
2 to 5 years
2+ years
minimum 3 years
at least 3 years
3 years of experience
6 months of experience
fresher

Source-specific behavior

LinkedIn and Naukri do not expose job data in exactly the same structure. The source scrapers therefore extract source-specific fields first, and the normalizer converts them to the common schema afterward.

Responsible Scraping

This project is intended for lawful research, personal job-search automation, and structured analysis.

Before running it at scale:

review the target site's Terms of Service

respect robots.txt and applicable site rules where relevant

use reasonable request rates

avoid bypassing authentication or access controls

do not collect unnecessary personal data

secure any credentials or cookies

Site HTML and access behavior can change, so scrapers may require maintenance over time.

License

Add the repository's chosen license here (for example, MIT) and include the corresponding LICENSE file in the repository.

If the repository already contains a license, keep that license text and update this section to match it exactly.

Author

Pravin Kumar A.

GitHub: https://github.com/Pravink1005

Project: https://github.com/Pravink1005/Job_Scraper