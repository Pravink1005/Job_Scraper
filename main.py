"""
Unified LinkedIn + Naukri Job Scraping Pipeline.

Pipeline flow:

    LinkedIn / Naukri
            ↓
       Orchestrator
            ↓
       Normalization
            ↓
       Validation
            ↓
       ML Enrichment
            ↓
       Deduplication
            ↓
     unified_jobs.csv
            ↓
        SQLite DB

IMPORTANT:
    ml/ml_predictor.py is kept completely unchanged.

SEARCH KEYWORDS:
    The common SEARCH_KEYWORDS list from config.py is used
    for both LinkedIn and Naukri.

Example in config.py:

    SEARCH_KEYWORDS = [
        "data analyst",
        "data scientist",
        "business analyst",
    ]
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Optional


# ============================================================
# PROJECT IMPORTS
# ============================================================

from config import (
    SEARCH_KEYWORDS,
    OUTPUT_DIR as CONFIG_OUTPUT_DIR,
    LINKEDIN_LOCATION,
    LINKEDIN_MAX_JOBS_PER_KEYWORD,
    LINKEDIN_MAX_AGE_HOURS,
    NAUKRI_MAX_PAGES,
    NAUKRI_MAX_JOBS,
    NAUKRI_MAX_TOTAL,
    NAUKRI_DELAY_SECONDS,
    NAUKRI_HEADLESS,
)

from pipeline.orchestrator import run_pipeline
from pipeline.storage import JobStore

from scrapers.linkedin.scraper import (
    collect_linkedin_jobs,
)

from scrapers.naukri.scraper import (
    collect_naukri_jobs,
)


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_OUTPUT_DIR = str(
    CONFIG_OUTPUT_DIR
)

CSV_FILENAME = "unified_jobs.csv"
DB_FILENAME = "jobs.db"


# ============================================================
# HELPERS
# ============================================================

def parse_bool(
    value: str | bool,
) -> bool:
    """
    Convert common string representations into bool.

    Examples:

        true
        false
        1
        0
        yes
        no
        on
        off
    """

    if isinstance(
        value,
        bool,
    ):
        return value

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    if normalized in {
        "true",
        "1",
        "yes",
        "y",
        "on",
    }:
        return True

    if normalized in {
        "false",
        "0",
        "no",
        "n",
        "off",
    }:
        return False

    raise argparse.ArgumentTypeError(
        f"Invalid boolean value: {value}"
    )


def split_csv(
    value: str,
) -> list[str]:
    """
    Convert comma-separated input into a clean list.

    Example:

        "data analyst, data scientist, business analyst"

    becomes:

        [
            "data analyst",
            "data scientist",
            "business analyst",
        ]
    """

    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


def build_naukri_search_url(
    keyword: str,
    job_age_days: int = 1,
) -> str:
    """
    Build a Naukri search URL from a job keyword.

    Example:

        data analyst

    becomes:

        https://www.naukri.com/data-analyst-jobs?jobAge=1
    """

    keyword = str(
        keyword
    ).strip()

    keyword_slug = (
        keyword
        .lower()
        .replace(" ", "-")
    )

    return (
        "https://www.naukri.com/"
        f"{keyword_slug}-jobs"
        f"?jobAge={job_age_days}"
    )


def build_naukri_search_urls(
    keywords: list[str],
) -> list[str]:
    """
    Build one Naukri search URL for each keyword.

    Example:

        [
            "data analyst",
            "data scientist",
            "business analyst",
        ]

    becomes:

        https://www.naukri.com/data-analyst-jobs?jobAge=1
        https://www.naukri.com/data-scientist-jobs?jobAge=1
        https://www.naukri.com/business-analyst-jobs?jobAge=1
    """

    search_urls = []

    for keyword in keywords:

        keyword = str(
            keyword
        ).strip()

        if not keyword:
            continue

        search_urls.append(
            build_naukri_search_url(
                keyword=keyword,
                job_age_days=1,
            )
        )

    return search_urls


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    By default, the search keywords come from config.py:

        SEARCH_KEYWORDS = [
            "data analyst",
            "data scientist",
            "business analyst",
        ]

    The command-line options can still temporarily override
    the configuration.
    """

    # --------------------------------------------------------
    # MASTER KEYWORDS FROM CONFIG
    # --------------------------------------------------------

    default_keywords = ",".join(
        SEARCH_KEYWORDS
    )

    parser = argparse.ArgumentParser(
        description=(
            "Unified LinkedIn + Naukri "
            "Job Scraping Pipeline"
        )
    )

    # ========================================================
    # GENERAL
    # ========================================================

    parser.add_argument(
        "--source",
        choices=[
            "linkedin",
            "naukri",
            "both",
        ],
        default="both",
        help="Job source to scrape.",
    )

    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory for CSV, state "
            "and SQLite output."
        ),
    )

    parser.add_argument(
        "--rebuild-output",
        action="store_true",
        help=(
            "Delete existing unified CSV/state "
            "before scraping."
        ),
    )

    parser.add_argument(
        "--no-enrichment",
        action="store_true",
        help="Disable ML enrichment.",
    )

    # ========================================================
    # LINKEDIN
    # ========================================================

    parser.add_argument(
        "--linkedin-keywords",
        default=default_keywords,
        help=(
            "Comma-separated LinkedIn keywords. "
            "Defaults to SEARCH_KEYWORDS from config.py."
        ),
    )

    parser.add_argument(
        "--linkedin-location",
        default=LINKEDIN_LOCATION,
        help="LinkedIn search location.",
    )

    parser.add_argument(
        "--linkedin-max-jobs",
        type=int,
        default=LINKEDIN_MAX_JOBS_PER_KEYWORD,
        help=(
            "Maximum LinkedIn jobs per keyword."
        ),
    )

    parser.add_argument(
        "--linkedin-max-age-hours",
        type=float,
        default=LINKEDIN_MAX_AGE_HOURS,
        help=(
            "Only collect LinkedIn jobs posted "
            "within the last N hours."
        ),
    )

    # ========================================================
    # NAUKRI
    # ========================================================

    parser.add_argument(
        "--naukri-titles",
        default=default_keywords,
        help=(
            "Comma-separated Naukri job titles. "
            "Defaults to SEARCH_KEYWORDS from config.py."
        ),
    )

    parser.add_argument(
        "--naukri-max-pages",
        type=int,
        default=NAUKRI_MAX_PAGES,
        help="Maximum Naukri pages per search.",
    )

    parser.add_argument(
        "--naukri-max-jobs",
        type=int,
        default=NAUKRI_MAX_JOBS,
        help="Maximum Naukri jobs per search.",
    )

    parser.add_argument(
        "--naukri-headless",
        type=parse_bool,
        default=NAUKRI_HEADLESS,
        help=(
            "Run Naukri browser headless: "
            "true/false."
        ),
    )

    return parser


# ============================================================
# SQLITE SYNC
# ============================================================

def sync_csv_to_sqlite(
    csv_path: Path,
    db_path: Path,
) -> bool:
    """
    Import unified_jobs.csv into the requested SQLite database.

    Existing records are updated using job_id.
    """

    if not csv_path.exists():

        print(
            f"[SQLite] CSV not found: {csv_path}"
        )

        return False

    print("")
    print("=" * 70)
    print("SQLITE DATABASE SYNC")
    print("=" * 70)

    print(
        f"[SQLite] CSV      : {csv_path}"
    )

    print(
        f"[SQLite] Database : {db_path}"
    )

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        source TEXT,
        title TEXT,
        company TEXT,
        category TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        min_experience_years TEXT,
        max_experience_years TEXT,
        salary TEXT,
        skills TEXT,
        degree_required TEXT,
        specialization_required TEXT,
        posted_time TEXT,
        collected_at TEXT,
        link TEXT,
        full_description TEXT
    )
    """

    connection = sqlite3.connect(
        db_path
    )

    cursor = connection.cursor()

    try:

        cursor.execute(
            create_table_sql
        )

        processed = 0
        skipped = 0

        with open(
            csv_path,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(
                file
            )

            required_fields = {
                "job_id",
                "source",
                "title",
                "company",
                "category",
                "city",
                "state",
                "country",
                "min_experience_years",
                "max_experience_years",
                "salary",
                "skills",
                "degree_required",
                "specialization_required",
                "posted_time",
                "collected_at",
                "link",
                "full_description",
            }

            actual_fields = set(
                reader.fieldnames or []
            )

            missing_fields = (
                required_fields
                - actual_fields
            )

            if missing_fields:

                raise ValueError(
                    "CSV is missing required "
                    f"fields: {sorted(missing_fields)}"
                )

            for row in reader:

                job_id = (
                    row.get(
                        "job_id"
                    )
                    or ""
                ).strip()

                if not job_id:

                    skipped += 1

                    continue

                values = (
                    job_id,

                    row.get(
                        "source",
                        "Not Specified",
                    ),

                    row.get(
                        "title",
                        "Not Specified",
                    ),

                    row.get(
                        "company",
                        "Not Specified",
                    ),

                    row.get(
                        "category",
                        "Not Specified",
                    ),

                    row.get(
                        "city",
                        "Not Specified",
                    ),

                    row.get(
                        "state",
                        "Not Specified",
                    ),

                    row.get(
                        "country",
                        "Not Specified",
                    ),

                    row.get(
                        "min_experience_years",
                        "Not Specified",
                    ),

                    row.get(
                        "max_experience_years",
                        "Not Specified",
                    ),

                    row.get(
                        "salary",
                        "Not Specified",
                    ),

                    row.get(
                        "skills",
                        "Not Specified",
                    ),

                    row.get(
                        "degree_required",
                        "Not Specified",
                    ),

                    row.get(
                        "specialization_required",
                        "Not Specified",
                    ),

                    row.get(
                        "posted_time",
                        "Not Specified",
                    ),

                    row.get(
                        "collected_at",
                        "Not Specified",
                    ),

                    row.get(
                        "link",
                        "Not Specified",
                    ),

                    row.get(
                        "full_description",
                        "Not Specified",
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO jobs (
                        job_id,
                        source,
                        title,
                        company,
                        category,
                        city,
                        state,
                        country,
                        min_experience_years,
                        max_experience_years,
                        salary,
                        skills,
                        degree_required,
                        specialization_required,
                        posted_time,
                        collected_at,
                        link,
                        full_description
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(job_id)
                    DO UPDATE SET
                        source = excluded.source,
                        title = excluded.title,
                        company = excluded.company,
                        category = excluded.category,
                        city = excluded.city,
                        state = excluded.state,
                        country = excluded.country,
                        min_experience_years =
                            excluded.min_experience_years,
                        max_experience_years =
                            excluded.max_experience_years,
                        salary = excluded.salary,
                        skills = excluded.skills,
                        degree_required =
                            excluded.degree_required,
                        specialization_required =
                            excluded.specialization_required,
                        posted_time =
                            excluded.posted_time,
                        collected_at =
                            excluded.collected_at,
                        link = excluded.link,
                        full_description =
                            excluded.full_description
                    """,
                    values,
                )

                processed += 1

        connection.commit()

        # ====================================================
        # INDEXES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jobs_source
            ON jobs(source)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jobs_company
            ON jobs(company)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jobs_city
            ON jobs(city)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_jobs_title
            ON jobs(title)
            """
        )

        connection.commit()

        # ====================================================
        # VERIFY DATABASE
        # ====================================================

        cursor.execute(
            "SELECT COUNT(*) FROM jobs"
        )

        total_jobs = (
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT source, COUNT(*)
            FROM jobs
            GROUP BY source
            ORDER BY source
            """
        )

        source_counts = (
            cursor.fetchall()
        )

        print("")

        print(
            f"Rows processed : "
            f"{processed + skipped}"
        )

        print(
            f"Skipped        : "
            f"{skipped}"
        )

        print(
            f"Total jobs DB  : "
            f"{total_jobs}"
        )

        print("")

        print(
            "Jobs by source:"
        )

        for source, count in source_counts:

            print(
                f"  {source}: {count}"
            )

        print("")

        print(
            f"SQLite database: {db_path}"
        )

        print("=" * 70)

        return True

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# PIPELINE REPORT
# ============================================================

def print_pipeline_report(
    report,
) -> None:
    """
    Display available RunReport fields without depending
    on one exact RunReport implementation.
    """

    print("")
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)

    fields = [
        (
            "Total collected",
            "total_collected",
        ),
        (
            "Total normalized",
            "total_normalized",
        ),
        (
            "Total skipped",
            "total_skipped",
        ),
        (
            "New rows written",
            "new_rows_written",
        ),
    ]

    for label, field in fields:

        if hasattr(
            report,
            field,
        ):

            print(
                f"{label:<18}: "
                f"{getattr(report, field)}"
            )


# ============================================================
# MAIN
# ============================================================

def main(
    argv: Optional[list[str]] = None,
) -> int:
    """
    Execute the complete scraping pipeline.
    """

    parser = build_parser()

    args = parser.parse_args(
        argv
    )

    output_dir = Path(
        args.output_dir
    )

    csv_path = (
        output_dir
        / CSV_FILENAME
    )

    db_path = (
        output_dir
        / DB_FILENAME
    )

    # ========================================================
    # KEYWORDS
    # ========================================================

    linkedin_keywords = split_csv(
        args.linkedin_keywords
    )

    naukri_titles = split_csv(
        args.naukri_titles
    )

    # ========================================================
    # HEADER
    # ========================================================

    print("")
    print("=" * 70)
    print("UNIFIED JOB SCRAPING PIPELINE")
    print("=" * 70)

    print(
        f"[Pipeline] Source        : "
        f"{args.source}"
    )

    print(
        f"[Pipeline] Output        : "
        f"{output_dir}"
    )

    print(
        f"[Pipeline] Rebuild       : "
        f"{args.rebuild_output}"
    )

    print(
        f"[Pipeline] ML enrichment : "
        f"{not args.no_enrichment}"
    )

    print("")

    print(
        "[Pipeline] Search Keywords:"
    )

    for index, keyword in enumerate(
        linkedin_keywords,
        start=1,
    ):

        print(
            f"  {index}. {keyword}"
        )

    print("=" * 70)

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # STORAGE
    # ========================================================

    store = JobStore(
        output_dir=output_dir
    )

    # ========================================================
    # REBUILD
    # ========================================================

    if args.rebuild_output:

        print("")

        print(
            "[Pipeline] "
            "Rebuild mode enabled"
        )

        # Reset CSV/state storage
        store.reset()

        # Reset SQLite database
        if db_path.exists():

            db_path.unlink()

            print(
                "[Pipeline] "
                "Existing SQLite database removed."
            )

    # ========================================================
    # LINKEDIN CONFIG
    # ========================================================

    linkedin_kwargs = {
        "keywords": linkedin_keywords,
        "location": args.linkedin_location,
        "max_jobs": args.linkedin_max_jobs,
        "max_age_hours": args.linkedin_max_age_hours,
    }

    # ========================================================
    # NAUKRI SEARCH URLS
    # ========================================================

    naukri_search_urls = (
        build_naukri_search_urls(
            naukri_titles
        )
    )

    # ========================================================
    # NAUKRI CONFIG
    # ========================================================

    naukri_kwargs = {
    "search_urls": naukri_search_urls,

    "titles": naukri_titles,

    "max_pages": (
        args.naukri_max_pages
    ),

    "max_total": (
        20
    ),

    "max_jobs": (
        args.naukri_max_jobs
    ),

    "headless": (
        args.naukri_headless
    ),

    "enable_detail_pages": (
        False
    ),
        }

    # ========================================================
    # SHOW NAUKRI SEARCH URLS
    # ========================================================

    if args.source in {
        "naukri",
        "both",
    }:

        print("")

        print(
            "[Pipeline] Naukri Search URLs:"
        )

        for index, url in enumerate(
            naukri_search_urls,
            start=1,
        ):

            print(
                f"  {index}. {url}"
            )

    # ========================================================
    # SELECT COLLECTORS
    # ========================================================

    linkedin_collector = None
    naukri_collector = None

    if args.source in {
        "linkedin",
        "both",
    }:

        linkedin_collector = (
            collect_linkedin_jobs
        )

    if args.source in {
        "naukri",
        "both",
    }:

        naukri_collector = (
            collect_naukri_jobs
        )

    # ========================================================
    # RUN SCRAPING PIPELINE
    # ========================================================

    try:

        report = run_pipeline(
            store=store,

            linkedin_collector=(
                linkedin_collector
            ),

            linkedin_kwargs=(
                linkedin_kwargs
                if linkedin_collector
                else None
            ),

            naukri_collector=(
                naukri_collector
            ),

            naukri_kwargs=(
                naukri_kwargs
                if naukri_collector
                else None
            ),

            apply_enrichment=(
                not args.no_enrichment
            ),
        )

    except TypeError as error:

        print("")
        print("=" * 70)
        print(
            "PIPELINE CONFIGURATION ERROR"
        )
        print("=" * 70)

        print(
            f"TypeError: {error}"
        )

        print("")

        print(
            "Check scraper function signatures "
            "and pipeline/orchestrator.py."
        )

        print("=" * 70)

        return 1

    except KeyboardInterrupt:

        print("")

        print(
            "[Pipeline] Interrupted by user."
        )

        return 130

    except Exception as error:

        print("")
        print("=" * 70)
        print("PIPELINE ERROR")
        print("=" * 70)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 70)

        return 1

    # ========================================================
    # REPORT
    # ========================================================

    print_pipeline_report(
        report
    )

    # ========================================================
    # SQLITE SYNC
    # ========================================================

    if not csv_path.exists():

        print("")

        print(
            f"[SQLite] CSV not found: "
            f"{csv_path}"
        )

        print(
            "[Pipeline] "
            "No SQLite sync performed."
        )

        return 1

    try:

        sqlite_success = (
            sync_csv_to_sqlite(
                csv_path=csv_path,
                db_path=db_path,
            )
        )

    except Exception as error:

        print("")
        print("=" * 70)
        print("SQLITE SYNC ERROR")
        print("=" * 70)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 70)

        return 1

    if not sqlite_success:

        return 1

    # ========================================================
    # FINAL
    # ========================================================

    print("")
    print("=" * 70)
    print(
        "PIPELINE FINISHED SUCCESSFULLY"
    )
    print("=" * 70)

    print(
        f"Unified CSV : "
        f"{csv_path}"
    )

    print(
        f"SQLite DB   : "
        f"{db_path}"
    )

    print("=" * 70)

    return 0


# ============================================================
# MAIN MODULE TESTS
# ============================================================

def _run_main_tests() -> None:
    """
    Test main.py helpers without starting either scraper.
    """

    print("=" * 70)
    print("MAIN MODULE TEST")
    print("=" * 70)

    # ========================================================
    # BOOLEAN PARSER
    # ========================================================

    assert parse_bool(
        "true"
    ) is True

    assert parse_bool(
        "TRUE"
    ) is True

    assert parse_bool(
        "yes"
    ) is True

    assert parse_bool(
        "1"
    ) is True

    assert parse_bool(
        "false"
    ) is False

    assert parse_bool(
        "no"
    ) is False

    assert parse_bool(
        "0"
    ) is False

    print(
        "[PASS] Boolean parser"
    )

    # ========================================================
    # CSV SPLITTER
    # ========================================================

    result = split_csv(
        "data analyst, data scientist, business analyst"
    )

    assert result == [
        "data analyst",
        "data scientist",
        "business analyst",
    ]

    print(
        "[PASS] CSV argument parser"
    )

    # ========================================================
    # EMPTY CSV VALUES
    # ========================================================

    result = split_csv(
        "data analyst,, ,data scientist"
    )

    assert result == [
        "data analyst",
        "data scientist",
    ]

    print(
        "[PASS] Empty CSV values removed"
    )

    # ========================================================
    # NAUKRI URL GENERATION
    # ========================================================

    test_url = build_naukri_search_url(
        "data analyst"
    )

    assert (
        test_url
        == (
            "https://www.naukri.com/"
            "data-analyst-jobs"
            "?jobAge=1"
        )
    )

    print(
        "[PASS] Naukri single URL generation"
    )

    # ========================================================
    # MULTIPLE NAUKRI URL GENERATION
    # ========================================================

    test_keywords = [
        "data analyst",
        "data scientist",
        "business analyst",
    ]

    naukri_urls = (
        build_naukri_search_urls(
            test_keywords
        )
    )

    assert (
        len(naukri_urls)
        == 3
    )

    assert (
        naukri_urls[0]
        == (
            "https://www.naukri.com/"
            "data-analyst-jobs"
            "?jobAge=1"
        )
    )

    assert (
        naukri_urls[1]
        == (
            "https://www.naukri.com/"
            "data-scientist-jobs"
            "?jobAge=1"
        )
    )

    assert (
        naukri_urls[2]
        == (
            "https://www.naukri.com/"
            "business-analyst-jobs"
            "?jobAge=1"
        )
    )

    print(
        "[PASS] Naukri multiple URL generation"
    )

    # ========================================================
    # CONFIG KEYWORDS
    # ========================================================

    assert (
        isinstance(
            SEARCH_KEYWORDS,
            list,
        )
    )

    assert (
        len(SEARCH_KEYWORDS)
        > 0
    )

    print(
        "[PASS] SEARCH_KEYWORDS loaded from config.py"
    )

    # ========================================================
    # DEFAULT ARGUMENTS
    # ========================================================

    parser = build_parser()

    args = parser.parse_args(
        []
    )

    assert (
        args.source
        == "both"
    )

    assert (
        args.output_dir
        == DEFAULT_OUTPUT_DIR
    )

    assert (
        args.linkedin_location
        == LINKEDIN_LOCATION
    )

    assert (
        args.linkedin_max_jobs
        == LINKEDIN_MAX_JOBS_PER_KEYWORD
    )

    assert (
        args.linkedin_max_age_hours
        == LINKEDIN_MAX_AGE_HOURS
    )

    assert (
        args.naukri_max_pages
        == NAUKRI_MAX_PAGES
    )

    assert (
        args.naukri_max_jobs
        == NAUKRI_MAX_JOBS
    )

    assert (
        args.naukri_headless
        == NAUKRI_HEADLESS
    )

    # LinkedIn and Naukri must both use
    # SEARCH_KEYWORDS by default.
    assert (
        split_csv(
            args.linkedin_keywords
        )
        == SEARCH_KEYWORDS
    )

    assert (
        split_csv(
            args.naukri_titles
        )
        == SEARCH_KEYWORDS
    )

    print(
        "[PASS] Argument defaults"
    )

    # ========================================================
    # LINKEDIN ARGUMENTS
    # ========================================================

    args = parser.parse_args(
        [
            "--source",
            "linkedin",
            "--linkedin-max-jobs",
            "10",
            "--linkedin-max-age-hours",
            "4",
        ]
    )

    assert (
        args.source
        == "linkedin"
    )

    assert (
        args.linkedin_max_jobs
        == 10
    )

    assert (
        args.linkedin_max_age_hours
        == 4.0
    )

    print(
        "[PASS] LinkedIn arguments"
    )

    # ========================================================
    # NAUKRI ARGUMENTS
    # ========================================================

    args = parser.parse_args(
        [
            "--source",
            "naukri",
            "--naukri-max-pages",
            "3",
            "--naukri-max-jobs",
            "15",
            "--naukri-headless",
            "false",
        ]
    )

    assert (
        args.source
        == "naukri"
    )

    assert (
        args.naukri_max_pages
        == 3
    )

    assert (
        args.naukri_max_jobs
        == 15
    )

    assert (
        args.naukri_headless
        is False
    )

    print(
        "[PASS] Naukri arguments"
    )

    # ========================================================
    # OUTPUT PATHS
    # ========================================================

    test_output = Path(
        "test_output"
    )

    assert (
        test_output / CSV_FILENAME
        == Path(
            "test_output/unified_jobs.csv"
        )
    )

    assert (
        test_output / DB_FILENAME
        == Path(
            "test_output/jobs.db"
        )
    )

    print(
        "[PASS] Output path construction"
    )

    # ========================================================
    # COMPLETE
    # ========================================================

    print("")
    print("=" * 70)
    print(
        "MAIN MODULE TEST PASSED"
    )
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # Run normal pipeline:
    #
    #     python main.py
    #
    # Run tests:
    #
    #     python main.py --test

    if "--test" in sys.argv:

        sys.argv.remove(
            "--test"
        )

        _run_main_tests()

    else:

        sys.exit(
            main()
        )