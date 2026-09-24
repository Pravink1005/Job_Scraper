"""
Unified job schema.

Both LinkedIn and Naukri produce different raw structures.

UnifiedJob is the single canonical representation used by:

    LinkedIn scraper
    Naukri scraper
          ↓
    Orchestrator
          ↓
    Normalizer
          ↓
    UnifiedJob
          ↓
    ML enrichment
          ↓
    Storage
          ↓
    unified_jobs.csv
          ↓
    SQLite

IMPORTANT:
    This file defines the data contract for the entire pipeline.
"""


from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import ClassVar


# ============================================================
# CONSTANTS
# ============================================================

NOT_SPECIFIED = "Not Specified"


# ============================================================
# CANONICAL CSV FIELD ORDER
# ============================================================

CSV_FIELDS = [
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
# UNIFIED JOB
# ============================================================

@dataclass
class UnifiedJob:
    """
    Canonical normalized representation of one job posting.

    Every scraper must eventually produce this structure.

    The fields are intentionally strings because the source
    websites can contain values such as:

        "2"
        "2-5"
        "Not Specified"
        "3+"
        "5 years"

    Experience parsing/normalization is handled upstream.
    """

    # --------------------------------------------------------
    # REQUIRED CORE FIELDS
    # --------------------------------------------------------

    job_id: str
    source: str
    title: str
    link: str

    # --------------------------------------------------------
    # COMPANY / SEARCH ORIGIN
    # --------------------------------------------------------

    company: str = NOT_SPECIFIED

    # The keyword that was searched for when this job was found
    # (e.g. "data analyst"). Lets you filter/group the dataset
    # by which search turned up each job.
    search_keyword: str = NOT_SPECIFIED

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    city: str = NOT_SPECIFIED
    state: str = NOT_SPECIFIED
    country: str = NOT_SPECIFIED

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    min_experience_years: str = NOT_SPECIFIED
    max_experience_years: str = NOT_SPECIFIED

    # --------------------------------------------------------
    # REQUIREMENTS
    # --------------------------------------------------------

    skills: str = NOT_SPECIFIED
    degree_required: str = NOT_SPECIFIED
    specialization_required: str = NOT_SPECIFIED

    # --------------------------------------------------------
    # TIMESTAMP / DESCRIPTION
    # --------------------------------------------------------

    collected_at: str = NOT_SPECIFIED

    full_description: str = NOT_SPECIFIED

    # --------------------------------------------------------
    # CANONICAL FIELD LIST
    # --------------------------------------------------------

    _CSV_FIELDS: ClassVar[
        list[str]
    ] = CSV_FIELDS

    # ========================================================
    # CSV CONVERSION
    # ========================================================

    def to_csv_row(self) -> dict:
        """
        Convert UnifiedJob into a dictionary using exactly the
        canonical CSV field order.

        Unknown/internal dataclass fields are ignored.
        """

        row = asdict(
            self
        )

        return {
            field: row.get(
                field,
                "",
            )
            for field in CSV_FIELDS
        }

    # ========================================================
    # CSV FIELDNAMES
    # ========================================================

    @classmethod
    def fieldnames(cls) -> list[str]:
        """
        Return the canonical CSV column order.
        """

        return list(
            cls._CSV_FIELDS
        )

    # ========================================================
    # DICTIONARY CONVERSION
    # ========================================================

    def to_dict(self) -> dict:
        """
        Return the complete UnifiedJob as a normal dictionary.

        Useful for debugging and ML enrichment.
        """

        return asdict(
            self
        )


# ============================================================
# MODULE TEST
# ============================================================

def _run_schema_tests() -> None:
    """
    Lightweight schema test.

    Does not touch the real CSV/database.
    """

    print("=" * 70)
    print("SCHEMA MODULE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Create test job
    # --------------------------------------------------------

    job = UnifiedJob(
        job_id="linkedin_test_001",
        source="LinkedIn",
        title="Data Analyst",
        company="Test Company",
        search_keyword="data analyst",
        city="Hyderabad",
        state="Telangana",
        country="India",
        min_experience_years="2",
        max_experience_years="5",
        skills="Python, SQL, Power BI",
        degree_required="B.E., Bachelor's",
        specialization_required="Data Science",
        collected_at="2026-09-22 10:00:00",
        link="https://example.com/job/1",
        full_description="Test job description",
    )

    # --------------------------------------------------------
    # Test required fields
    # --------------------------------------------------------

    assert (
        job.job_id
        == "linkedin_test_001"
    )

    assert (
        job.source
        == "LinkedIn"
    )

    assert (
        job.title
        == "Data Analyst"
    )

    print(
        "[PASS] UnifiedJob creation"
    )

    # --------------------------------------------------------
    # Test default values
    # --------------------------------------------------------

    default_job = UnifiedJob(
        job_id="test_default",
        source="LinkedIn",
        title="Test Job",
        link="https://example.com",
    )

    assert (
        default_job.company
        == "Not Specified"
    )

    assert (
        default_job.city
        == "Not Specified"
    )

    assert (
        default_job.state
        == "Not Specified"
    )

    assert (
        default_job.country
        == "Not Specified"
    )

    assert (
        default_job.skills
        == "Not Specified"
    )

    assert (
        default_job.degree_required
        == "Not Specified"
    )

    print(
        "[PASS] Default values"
    )

    # --------------------------------------------------------
    # Test CSV field count
    # --------------------------------------------------------

    fields = (
        UnifiedJob.fieldnames()
    )

    assert (
        len(fields)
        == 16
    )

    assert (
        fields
        == CSV_FIELDS
    )

    print(
        "[PASS] CSV field order"
    )

    # --------------------------------------------------------
    # Test CSV conversion
    # --------------------------------------------------------

    row = (
        job.to_csv_row()
    )

    assert (
        list(row.keys())
        == CSV_FIELDS
    )

    assert (
        row["job_id"]
        == "linkedin_test_001"
    )

    assert (
        row["title"]
        == "Data Analyst"
    )

    assert (
        row["company"]
        == "Test Company"
    )

    assert (
        row["city"]
        == "Hyderabad"
    )

    assert (
        row["state"]
        == "Telangana"
    )

    assert (
        row["country"]
        == "India"
    )

    print(
        "[PASS] CSV row conversion"
    )

    # --------------------------------------------------------
    # Test dictionary conversion
    # --------------------------------------------------------

    data = (
        job.to_dict()
    )

    assert isinstance(
        data,
        dict,
    )

    assert (
        data["job_id"]
        == "linkedin_test_001"
    )

    print(
        "[PASS] Dictionary conversion"
    )

    # --------------------------------------------------------
    # Verify no extra CSV columns
    # --------------------------------------------------------

    assert (
        set(row.keys())
        == set(CSV_FIELDS)
    )

    print(
        "[PASS] No extra CSV columns"
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "SCHEMA MODULE TEST PASSED"
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    _run_schema_tests()