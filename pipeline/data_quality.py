"""
pipeline/data_quality.py

Production Data Quality Audit
------------------------------

Checks the actual unified job dataset for:

1. Duplicate job IDs
2. Missing job IDs
3. Missing title/company
4. Invalid sources
5. Polluted city/state/country
6. LinkedIn metadata contamination
7. Education regex contamination
8. Invalid experience values
9. Missing links
10. CSV <-> SQLite consistency
11. Source counts
12. Basic data completeness

Run:
    python -m pipeline.data_quality

Expected files:
    csv_output/unified_jobs.csv
    csv_output/jobs.db
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from config import OUTPUT_DIR


# ============================================================
# CONFIGURATION
#
# CSV_PATH / DB_PATH are derived from config.OUTPUT_DIR so this
# audit always checks the same files main.py/database.py write
# to (respecting PIPELINE_OUTPUT_DIR). Do not hardcode
# "csv_output" here again.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = OUTPUT_DIR / "unified_jobs.csv"
DB_PATH = OUTPUT_DIR / "jobs.db"

EXPECTED_SOURCES = {"linkedin", "naukri"}

NOT_SPECIFIED_VALUES = {
    "",
    "not specified",
    "not_specified",
    "n/a",
    "na",
    "none",
    "null",
    "-",
}


# ============================================================
# EXPECTED CSV COLUMNS
# ============================================================

EXPECTED_COLUMNS = [
    "job_id",
    "source",
    "title",
    "company",
    "search_keyword",
    "city",
    "state",
    "country",
    "min_experience_years",
    "max_experience_years",
    "skills",
    "degree_required",
    "specialization_required",
    "collected_at",
    "link",
    "full_description",
]


# ============================================================
# HELPERS
# ============================================================

def is_missing(value) -> bool:
    """Return True when a value represents a missing field."""

    if value is None:
        return True

    text = str(value).strip().lower()

    return text in NOT_SPECIFIED_VALUES


def clean(value) -> str:
    """Convert a value to a normalized string."""

    if value is None:
        return ""

    return str(value).strip()


def is_number(value) -> bool:
    """Check whether a value is numeric."""

    if is_missing(value):
        return True

    try:
        float(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


# ============================================================
# CSV LOADING
# ============================================================

def load_csv() -> Tuple[List[Dict[str, str]], List[str]]:
    """Load the unified CSV."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found:\n{CSV_PATH}"
        )

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames or []

        rows = list(reader)

    return rows, columns


# ============================================================
# LOCATION VALIDATION
# ============================================================

INDIAN_STATES = {
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "delhi",
    "jammu and kashmir",
    "ladakh",
    "puducherry",
    "chandigarh",
}


LINKEDIN_METADATA_PATTERNS = [
    r"\b\d+\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago\b",
    r"\b\d+\s+applicants?\b",
    r"\bbe\s+among\s+the\s+first\b",
    r"\bpromoted\b",
    r"\beasy\s+apply\b",
    r"\bactively\s+recruiting\b",
    r"\bpeople\s+clicked\s+apply\b",
]


EDUCATION_GARBAGE_PATTERNS = [
    r"\\\.",
    r"\(\?:",
    r"\?:",
    r"\(\?=",
    r"\(\?!",
    r"\[\^",
]


# ============================================================
# LOCATION CHECKS
# ============================================================

def is_polluted_location_value(value: str) -> bool:
    """
    Detect obvious LinkedIn metadata or scraper contamination.
    """

    text = clean(value)

    if is_missing(text):
        return False

    for pattern in LINKEDIN_METADATA_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    # Obvious concatenated Indian location corruption
    if re.search(
        r"(telangana|karnataka|tamil\s*nadu|kerala|maharashtra|"
        r"gujarat|haryana|delhi|west\s*bengal|rajasthan|"
        r"uttar\s*pradesh|madhya\s*pradesh)india$",
        text,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def is_polluted_city(value: str) -> bool:
    """Detect likely polluted city values."""

    text = clean(value)

    if is_missing(text):
        return False

    if is_polluted_location_value(text):
        return True

    # Company + city contamination patterns
    suspicious_patterns = [
        r"^StateStreet\s+",
        r"^AmericanExpress\s+",
        r"^GLOBELANCE\s+",
        r"^Crunchyroll\s+",
        r"^Capco\s+",
        r"^TriNetTriNet\s+",
        r"^Andaz\s+",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    return False


def is_polluted_state(value: str) -> bool:
    """Detect likely polluted state values."""

    text = clean(value)

    if is_missing(text):
        return False

    if is_polluted_location_value(text):
        return True

    # Concatenated state + country
    if re.search(
        r"(telangana|karnataka|tamil\s*nadu|kerala|"
        r"maharashtra|gujarat|haryana|delhi|west\s*bengal|"
        r"rajasthan|uttar\s*pradesh|madhya\s*pradesh)india$",
        text,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def is_polluted_country(value: str) -> bool:
    """Detect country values containing metadata."""

    text = clean(value)

    if is_missing(text):
        return False

    if is_polluted_location_value(text):
        return True

    # Country should generally be just India for Indian jobs.
    if "india" in text.lower() and text.lower() != "india":
        return True

    return False


# ============================================================
# EDUCATION CHECK
# ============================================================

def is_polluted_education(value: str) -> bool:
    """Detect regex/code artifacts inside education."""

    text = clean(value)

    if is_missing(text):
        return False

    for pattern in EDUCATION_GARBAGE_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


# ============================================================
# CSV STRUCTURE CHECK
# ============================================================

def check_csv_structure(
    columns: List[str],
) -> List[str]:

    problems = []

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in columns
    ]

    extra_columns = [
        column
        for column in columns
        if column not in EXPECTED_COLUMNS
    ]

    if missing_columns:
        problems.append(
            f"Missing columns: {missing_columns}"
        )

    if extra_columns:
        problems.append(
            f"Unexpected columns: {extra_columns}"
        )

    return problems


# ============================================================
# DUPLICATE CHECK
# ============================================================

def check_duplicate_ids(
    rows: List[Dict[str, str]],
) -> List[Tuple[str, int]]:

    counter = Counter()

    for row in rows:

        job_id = clean(row.get("job_id"))

        if job_id:
            counter[job_id] += 1

    duplicates = [
        (job_id, count)
        for job_id, count in counter.items()
        if count > 1
    ]

    return sorted(
        duplicates,
        key=lambda item: item[1],
        reverse=True,
    )


# ============================================================
# MISSING FIELD CHECK
# ============================================================

def find_missing_field(
    rows: List[Dict[str, str]],
    field: str,
) -> List[int]:

    bad_rows = []

    for index, row in enumerate(rows, start=2):

        if is_missing(row.get(field)):

            bad_rows.append(index)

    return bad_rows


# ============================================================
# SOURCE CHECK
# ============================================================

def check_sources(
    rows: List[Dict[str, str]],
) -> Tuple[Counter, List[Tuple[int, str]]]:

    counter = Counter()
    invalid = []

    for index, row in enumerate(rows, start=2):

        source = clean(row.get("source")).lower()

        counter[source] += 1

        if source not in EXPECTED_SOURCES:

            invalid.append(
                (index, source)
            )

    return counter, invalid


# ============================================================
# EXPERIENCE CHECK
# ============================================================

def check_experience(
    rows: List[Dict[str, str]],
) -> List[Tuple[int, str, str]]:

    problems = []

    for index, row in enumerate(rows, start=2):

        min_exp = clean(
            row.get("min_experience_years")
        )

        max_exp = clean(
            row.get("max_experience_years")
        )

        if not is_number(min_exp):
            problems.append(
                (index, "min_experience_years", min_exp)
            )

        if not is_number(max_exp):
            problems.append(
                (index, "max_experience_years", max_exp)
            )

        # Check logical relationship
        if (
            is_number(min_exp)
            and is_number(max_exp)
            and not is_missing(min_exp)
            and not is_missing(max_exp)
        ):

            try:

                min_value = float(min_exp)
                max_value = float(max_exp)

                if min_value > max_value:

                    problems.append(
                        (
                            index,
                            "experience_range",
                            f"{min_value} > {max_value}",
                        )
                    )

            except ValueError:
                pass

    return problems


# ============================================================
# DATA QUALITY AUDIT
# ============================================================

def audit_csv(
    rows: List[Dict[str, str]],
    columns: List[str],
) -> Dict:

    results = {}

    results["total_rows"] = len(rows)

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    results["structure_problems"] = check_csv_structure(
        columns
    )

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    results["duplicate_ids"] = check_duplicate_ids(
        rows
    )

    # --------------------------------------------------------
    # Missing fields
    # --------------------------------------------------------

    required_fields = [
        "job_id",
        "source",
        "title",
        "company",
        "link",
    ]

    results["missing_fields"] = {}

    for field in required_fields:

        results["missing_fields"][field] = (
            find_missing_field(rows, field)
        )

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    source_counts, invalid_sources = check_sources(
        rows
    )

    results["source_counts"] = source_counts
    results["invalid_sources"] = invalid_sources

    # --------------------------------------------------------
    # Location contamination
    # --------------------------------------------------------

    results["polluted_city"] = []
    results["polluted_state"] = []
    results["polluted_country"] = []

    for index, row in enumerate(rows, start=2):

        city = row.get("city", "")
        state = row.get("state", "")
        country = row.get("country", "")

        if is_polluted_city(city):

            results["polluted_city"].append(
                (index, clean(city))
            )

        if is_polluted_state(state):

            results["polluted_state"].append(
                (index, clean(state))
            )

        if is_polluted_country(country):

            results["polluted_country"].append(
                (index, clean(country))
            )

    # --------------------------------------------------------
    # Education contamination
    # --------------------------------------------------------

    results["polluted_education"] = []

    for index, row in enumerate(rows, start=2):

        education = row.get(
            "degree_required",
            "",
        )

        if is_polluted_education(education):

            results["polluted_education"].append(
                (index, clean(education))
            )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    results["experience_problems"] = (
        check_experience(rows)
    )

    # --------------------------------------------------------
    # Missing links
    # --------------------------------------------------------

    results["missing_links"] = find_missing_field(
        rows,
        "link",
    )

    return results


# ============================================================
# SQLITE CHECK
# ============================================================

def load_sqlite_stats() -> Dict:

    results = {
        "exists": DB_PATH.exists(),
        "total": 0,
        "sources": Counter(),
        "job_ids": set(),
        "error": None,
    }

    if not DB_PATH.exists():

        results["error"] = (
            f"SQLite database not found: {DB_PATH}"
        )

        return results

    try:

        connection = sqlite3.connect(
            DB_PATH
        )

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Total
        # ----------------------------------------------------

        cursor.execute(
            "SELECT COUNT(*) FROM jobs"
        )

        row = cursor.fetchone()

        if row:
            results["total"] = row[0]

        # ----------------------------------------------------
        # Source counts
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT source, COUNT(*)
            FROM jobs
            GROUP BY source
            """
        )

        for source, count in cursor.fetchall():

            results["sources"][
                clean(source).lower()
            ] = count

        # ----------------------------------------------------
        # Job IDs
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT job_id
            FROM jobs
            WHERE job_id IS NOT NULL
            """
        )

        results["job_ids"] = {
            clean(row[0])
            for row in cursor.fetchall()
            if clean(row[0])
        }

        connection.close()

    except Exception as exc:

        results["error"] = str(exc)

    return results


# ============================================================
# CSV <-> SQLITE COMPARISON
# ============================================================

def compare_csv_sqlite(
    csv_rows: List[Dict[str, str]],
    sqlite_stats: Dict,
) -> Dict:

    csv_ids = {
        clean(row.get("job_id"))
        for row in csv_rows
        if clean(row.get("job_id"))
    }

    sqlite_ids = sqlite_stats.get(
        "job_ids",
        set(),
    )

    return {
        "csv_total": len(csv_rows),
        "sqlite_total": sqlite_stats.get(
            "total",
            0,
        ),
        "csv_ids": len(csv_ids),
        "sqlite_ids": len(sqlite_ids),
        "missing_in_sqlite": sorted(
            csv_ids - sqlite_ids
        ),
        "missing_in_csv": sorted(
            sqlite_ids - csv_ids
        ),
    }


# ============================================================
# REPORT HELPERS
# ============================================================

def print_problem_list(
    title: str,
    problems,
    max_items: int = 20,
):
    """Print a problem list without flooding the terminal."""

    count = len(problems)

    if count == 0:

        print(f"[PASS] {title}: 0")
        return

    print(
        f"[FAIL] {title}: {count}"
    )

    for item in problems[:max_items]:

        print(f"       {item}")

    if count > max_items:

        print(
            f"       ... and {count - max_items} more"
        )


def print_missing_fields(
    missing_fields: Dict[str, List[int]],
):
    """Print missing required fields."""

    for field, rows in missing_fields.items():

        if rows:

            print(
                f"[FAIL] Missing {field}: "
                f"{len(rows)} rows"
            )

            print(
                f"       CSV rows: {rows[:20]}"
            )

        else:

            print(
                f"[PASS] Missing {field}: 0"
            )


# ============================================================
# FINAL STATUS
# ============================================================

def calculate_final_status(
    audit: Dict,
    sqlite_stats: Dict,
    comparison: Dict,
) -> bool:

    checks = []

    # Structure
    checks.append(
        len(audit["structure_problems"]) == 0
    )

    # Duplicate IDs
    checks.append(
        len(audit["duplicate_ids"]) == 0
    )

    # Missing required fields
    for rows in audit["missing_fields"].values():

        checks.append(
            len(rows) == 0
        )

    # Sources
    checks.append(
        len(audit["invalid_sources"]) == 0
    )

    # Location
    checks.append(
        len(audit["polluted_city"]) == 0
    )

    checks.append(
        len(audit["polluted_state"]) == 0
    )

    checks.append(
        len(audit["polluted_country"]) == 0
    )

    # Education
    checks.append(
        len(audit["polluted_education"]) == 0
    )

    # Experience
    checks.append(
        len(audit["experience_problems"]) == 0
    )

    # SQLite
    if sqlite_stats["exists"]:

        checks.append(
            sqlite_stats["error"] is None
        )

        checks.append(
            comparison["csv_total"]
            == comparison["sqlite_total"]
        )

        checks.append(
            len(
                comparison["missing_in_sqlite"]
            )
            == 0
        )

        checks.append(
            len(
                comparison["missing_in_csv"]
            )
            == 0
        )

    return all(checks)


# ============================================================
# MAIN AUDIT
# ============================================================

def run_audit() -> bool:

    print("=" * 72)
    print("PRODUCTION DATA QUALITY AUDIT")
    print("=" * 72)

    print()
    print(f"Project root : {PROJECT_ROOT}")
    print(f"CSV          : {CSV_PATH}")
    print(f"SQLite       : {DB_PATH}")

    # --------------------------------------------------------
    # Load CSV
    # --------------------------------------------------------

    try:

        rows, columns = load_csv()

    except Exception as exc:

        print()
        print("[FAIL] Could not load CSV")
        print(f"       {exc}")

        return False

    print()
    print("-" * 72)
    print("CSV OVERVIEW")
    print("-" * 72)

    print(f"Rows         : {len(rows)}")
    print(f"Columns      : {len(columns)}")

    # --------------------------------------------------------
    # Audit
    # --------------------------------------------------------

    audit = audit_csv(
        rows,
        columns,
    )

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("CSV STRUCTURE")
    print("-" * 72)

    if audit["structure_problems"]:

        for problem in audit[
            "structure_problems"
        ]:

            print(
                f"[FAIL] {problem}"
            )

    else:

        print(
            "[PASS] CSV contains expected 16 columns"
        )

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("JOB ID CHECK")
    print("-" * 72)

    print_problem_list(
        "Duplicate job_id",
        audit["duplicate_ids"],
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("REQUIRED FIELD CHECK")
    print("-" * 72)

    print_missing_fields(
        audit["missing_fields"]
    )

    # --------------------------------------------------------
    # Sources
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("SOURCE CHECK")
    print("-" * 72)

    for source, count in sorted(
        audit["source_counts"].items()
    ):

        print(
            f"{source or '<empty>':12} : {count}"
        )

    print_problem_list(
        "Invalid source",
        audit["invalid_sources"],
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("LOCATION QUALITY")
    print("-" * 72)

    print_problem_list(
        "Polluted city",
        audit["polluted_city"],
    )

    print_problem_list(
        "Polluted state",
        audit["polluted_state"],
    )

    print_problem_list(
        "Polluted country",
        audit["polluted_country"],
    )

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("EDUCATION QUALITY")
    print("-" * 72)

    print_problem_list(
        "Education regex contamination",
        audit["polluted_education"],
    )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("EXPERIENCE QUALITY")
    print("-" * 72)

    print_problem_list(
        "Experience problems",
        audit["experience_problems"],
    )

    # --------------------------------------------------------
    # Links
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("LINK QUALITY")
    print("-" * 72)

    print_problem_list(
        "Missing links",
        audit["missing_links"],
    )

    # --------------------------------------------------------
    # SQLite
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("SQLITE CHECK")
    print("-" * 72)

    sqlite_stats = load_sqlite_stats()

    if not sqlite_stats["exists"]:

        print(
            "[FAIL] SQLite database does not exist"
        )

    elif sqlite_stats["error"]:

        print(
            "[FAIL] SQLite error:"
        )

        print(
            f"       {sqlite_stats['error']}"
        )

    else:

        print(
            f"[PASS] SQLite total rows: "
            f"{sqlite_stats['total']}"
        )

        print()
        print("SQLite jobs by source:")

        for source, count in sorted(
            sqlite_stats["sources"].items()
        ):

            print(
                f"  {source}: {count}"
            )

    # --------------------------------------------------------
    # CSV <-> SQLite
    # --------------------------------------------------------

    print()
    print("-" * 72)
    print("CSV <-> SQLITE CONSISTENCY")
    print("-" * 72)

    comparison = compare_csv_sqlite(
        rows,
        sqlite_stats,
    )

    print(
        f"CSV rows       : "
        f"{comparison['csv_total']}"
    )

    print(
        f"SQLite rows    : "
        f"{comparison['sqlite_total']}"
    )

    print(
        f"CSV job IDs    : "
        f"{comparison['csv_ids']}"
    )

    print(
        f"SQLite job IDs : "
        f"{comparison['sqlite_ids']}"
    )

    print_problem_list(
        "CSV jobs missing in SQLite",
        comparison["missing_in_sqlite"],
    )

    print_problem_list(
        "SQLite jobs missing in CSV",
        comparison["missing_in_csv"],
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    passed = calculate_final_status(
        audit,
        sqlite_stats,
        comparison,
    )

    print()
    print("=" * 72)

    if passed:

        print(
            "DATABASE / DATA QUALITY AUDIT PASSED"
        )

        print("=" * 72)

        print()
        print(
            "Your production dataset passed all "
            "quality checks."
        )

    else:

        print(
            "DATABASE / DATA QUALITY AUDIT FAILED"
        )

        print("=" * 72)

        print()
        print(
            "One or more quality checks require attention."
        )

    print()

    return passed


# ============================================================
# TESTS
# ============================================================

def run_module_tests():

    print("=" * 72)
    print("DATA QUALITY MODULE TEST")
    print("=" * 72)

    # Missing values
    assert is_missing("")
    assert is_missing("Not Specified")
    assert is_missing("N/A")
    assert not is_missing("India")

    print("[PASS] Missing value detection")

    # Location metadata
    assert is_polluted_location_value(
        "Mumbai Metropolitan Region 48 minutes ago"
    )

    assert is_polluted_location_value(
        "Hyderabad, TelanganaIndia"
    )

    assert not is_polluted_location_value(
        "Hyderabad, Telangana, India"
    )

    print("[PASS] Location contamination detection")

    # City
    assert is_polluted_city(
        "Crunchyroll Hyderabad"
    )

    assert not is_polluted_city(
        "Hyderabad"
    )

    print("[PASS] City contamination detection")

    # Education
    assert is_polluted_education(
        r"B\.?E\., Bachelor(?:'s)?"
    )

    assert not is_polluted_education(
        "B.E., Bachelor's, degree"
    )

    print("[PASS] Education contamination detection")

    # Experience
    assert is_number("2")
    assert is_number("5")
    assert is_number("Not Specified")
    assert not is_number("two years")

    print("[PASS] Experience validation")

    # Expected columns
    assert len(EXPECTED_COLUMNS) == 16

    print("[PASS] CSV schema definition")

    print()
    print(
        "DATA QUALITY MODULE TEST PASSED"
    )

    print("=" * 72)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # Run lightweight unit tests first
    run_module_tests()

    print()

    # Run production audit
    success = run_audit()

    # Return appropriate process status
    raise SystemExit(
        0 if success else 1
    )