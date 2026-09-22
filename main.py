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
"""


from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Callable, Optional


# ============================================================
# PROJECT IMPORTS
# ============================================================

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

DEFAULT_OUTPUT_DIR = "csv_output"
CSV_FILENAME = "unified_jobs.csv"
DB_FILENAME = "jobs.db"


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Unified LinkedIn + Naukri "
            "Job Scraping Pipeline"
        )
    )

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

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
        help="Directory for CSV, state and SQLite output.",
    )

    parser.add_argument(
        "--rebuild-output",
        action="store_true",
        help="Delete existing unified CSV/state before scraping.",
    )

    parser.add_argument(
        "--no-enrichment",
        action="store_true",
        help="Disable ML enrichment.",
    )

    # --------------------------------------------------------
    # LINKEDIN
    # --------------------------------------------------------

    parser.add_argument(
        "--linkedin-keywords",
        default=(
            "data analyst,"
        ),
        help="Comma-separated LinkedIn keywords.",
    )

    parser.add_argument(
        "--linkedin-location",
        default="India",
        help="LinkedIn search location.",
    )

    parser.add_argument(
        "--linkedin-max-jobs",
        type=int,
        default=100,
        help="Maximum LinkedIn jobs.",
    )

    parser.add_argument(
        "--linkedin-max-age-hours",
        type=float,
        default=24.0,
        help="Only collect LinkedIn jobs posted within the last N hours.",
    )

    # --------------------------------------------------------
    # NAUKRI
    # --------------------------------------------------------

    parser.add_argument(
        "--naukri-titles",
        default="data analyst",
        help="Comma-separated Naukri job titles.",
    )

    parser.add_argument(
        "--naukri-max-pages",
        type=int,
        default=5,
        help="Maximum Naukri pages.",
    )

    parser.add_argument(
        "--naukri-max-jobs",
        type=int,
        default=20,
        help="Maximum Naukri jobs.",
    )

    parser.add_argument(
        "--naukri-headless",
        type=parse_bool,
        default=True,
        help="Run Naukri browser headless: true/false.",
    )

    return parser


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
    """

    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


# ============================================================
# SQLITE SYNC
# ============================================================

def sync_csv_to_sqlite(
    csv_path: Path,
    db_path: Path,
) -> bool:
    """
    Import unified_jobs.csv into the requested SQLite database.

    This implementation is intentionally local to main.py so
    --output-dir works correctly.

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

        inserted = 0
        updated = 0
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
                    row.get("job_id")
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
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?
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

                # SQLite's rowcount is not a reliable
                # insert/update distinction for every
                # SQLite version, so we simply count
                # processed rows here.
                inserted += 1

        connection.commit()

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # VERIFY DATABASE
        # ----------------------------------------------------

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
            f"{inserted + skipped}"
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
        print("Jobs by source:")

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

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

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

    print("=" * 70)

    # --------------------------------------------------------
    # OUTPUT DIRECTORY
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    store = JobStore(
        output_dir=output_dir
    )

    # --------------------------------------------------------
    # REBUILD
    # --------------------------------------------------------

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
                "[Pipeline] Existing SQLite database removed."
            )

    # --------------------------------------------------------
    # LINKEDIN CONFIG
    # --------------------------------------------------------

    linkedin_kwargs = {
        "keywords": split_csv(
            args.linkedin_keywords
        ),
        "location": args.linkedin_location,
        "max_jobs": args.linkedin_max_jobs,
        "max_age_hours": args.linkedin_max_age_hours,
    }

    # --------------------------------------------------------
    # NAUKRI CONFIG
    # --------------------------------------------------------

    naukri_kwargs = {
        "titles": split_csv(
            args.naukri_titles
        ),
        "max_pages": args.naukri_max_pages,
        "max_jobs": args.naukri_max_jobs,
        "headless": args.naukri_headless,
    }

    # --------------------------------------------------------
    # SELECT COLLECTORS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RUN SCRAPING PIPELINE
    # --------------------------------------------------------

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
        print("PIPELINE CONFIGURATION ERROR")
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

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print_pipeline_report(
        report
    )

    # --------------------------------------------------------
    # SQLITE SYNC
    # --------------------------------------------------------

    if not csv_path.exists():

        print("")
        print(
            f"[SQLite] CSV not found: "
            f"{csv_path}"
        )

        print(
            "[Pipeline] No SQLite sync performed."
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

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print("")
    print("=" * 70)
    print("PIPELINE FINISHED SUCCESSFULLY")
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

    # --------------------------------------------------------
    # Boolean parser
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CSV splitter
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Empty CSV splitter
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Parser defaults
    # --------------------------------------------------------

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
        == "India"
    )

    assert (
        args.linkedin_max_age_hours
        == 24.0
    )

    assert (
        args.naukri_headless
        is True
    )

    print(
        "[PASS] Argument defaults"
    )

    # --------------------------------------------------------
    # Parser source selection
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Naukri arguments
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Path construction
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

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

    # Run normal pipeline when arguments are supplied.
    #
    # Run:
    #     python main.py
    #
    # Run module:
    #     python -m main
    #
    # Run tests:
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