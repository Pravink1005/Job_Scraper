"""
Pipeline orchestrator.

Workflow:

    scrape
        ↓
    source field adapter
        ↓
    normalize
        ↓
    UnifiedJob
        ↓
    enrichment / ml_predictor
        ↓
    dedupe
        ↓
    unified CSV

LinkedIn and Naukri are isolated from each other.

IMPORTANT:
    ml_predictor / enrichment code is NOT modified here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Any

from .enrichment import enrich_job
from .errors import DataValidationError, PipelineError, ScraperError
from .normalizer import normalize
from .schema import UnifiedJob
from .storage import JobStore


# ============================================================
# CONSTANTS
# ============================================================

NOT_SPECIFIED = "Not Specified"


# ============================================================
# RESULT CLASSES
# ============================================================

@dataclass
class SourceResult:
    source: str
    collected: int = 0
    normalized: int = 0
    skipped_invalid: int = 0
    error: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass
class RunReport:
    results: List[SourceResult] = field(default_factory=list)
    new_jobs_written: int = 0

    @property
    def total_collected(self) -> int:
        return sum(
            result.collected
            for result in self.results
        )

    @property
    def any_source_failed(self) -> bool:
        return any(
            not result.succeeded
            for result in self.results
        )

    def summary(self) -> str:
        lines = []

        for result in self.results:

            if result.succeeded:

                lines.append(
                    f"  {result.source}: "
                    f"collected={result.collected}, "
                    f"normalized={result.normalized}, "
                    f"skipped_invalid={result.skipped_invalid}"
                )

            else:

                lines.append(
                    f"  {result.source}: "
                    f"FAILED - {result.error}"
                )

        lines.append(
            f"  New rows written to unified CSV: "
            f"{self.new_jobs_written}"
        )

        return "\n".join(lines)


# ============================================================
# TEXT HELPERS
# ============================================================

def _clean(value: Any) -> str:
    """
    Convert a value into clean text.

    Lists / tuples / sets are converted into comma-separated
    text.
    """

    if value is None:
        return ""

    if isinstance(
        value,
        (list, tuple, set),
    ):

        value = ", ".join(
            str(item)
            for item in value
            if item is not None
        )

    value = str(value)

    value = " ".join(
        value.split()
    )

    return value.strip()


def _first_value(
    data: dict,
    *keys: str,
) -> str:
    """
    Return the first non-empty value.
    """

    for key in keys:

        if key not in data:
            continue

        value = _clean(
            data.get(key)
        )

        if value:
            return value

    return ""


# ============================================================
# SOURCE FIELD ADAPTER
# ============================================================

def _adapt_source_job(
    source_key: str,
    raw: dict,
) -> dict:
    """
    Convert scraper-specific field names into the common
    field names expected by pipeline.normalizer.

    This function ONLY maps field names.

    It does NOT attempt to clean location, education,
    company names, dates, etc.

    That responsibility belongs to normalizer.py.
    """

    if not isinstance(raw, dict):

        return raw

    adapted = dict(raw)

    source_lower = (
        source_key
        .strip()
        .lower()
    )

    # ========================================================
    # SOURCE
    # ========================================================

    source = _first_value(
        raw,
        "source",
        "Source",
        "platform",
    )

    if not source:

        if source_lower == "linkedin":
            source = "LinkedIn"

        elif source_lower == "naukri":
            source = "Naukri"

        else:
            source = source_key

    adapted["source"] = source

    # ========================================================
    # TITLE
    # ========================================================

    title = _first_value(
        raw,
        "job_title",
        "title",
        "Job Title",
        "jobTitle",
        "name",
    )

    if title:

        adapted["title"] = title
        adapted["job_title"] = title
        adapted["Job Title"] = title

    # ========================================================
    # COMPANY
    # ========================================================

    company = _first_value(
        raw,
        "company_name",
        "company",
        "Company Name",
        "companyName",
    )

    if company:

        adapted["company"] = company
        adapted["company_name"] = company
        adapted["Company Name"] = company

    # ========================================================
    # LOCATION
    # ========================================================

    location = _first_value(
        raw,
        "location",
        "locations",
        "Location",
        "Location(s)",
    )

    if location:

        adapted["location"] = location
        adapted["locations"] = location
        adapted["Location"] = location
        adapted["Location(s)"] = location

    # ========================================================
    # DESCRIPTION
    # ========================================================

    description = _first_value(
        raw,
        "job_description",
        "description",
        "Job Description",
        "jobDescription",
        "full_description",
    )

    if description:

        adapted["description"] = description
        adapted["job_description"] = description
        adapted["full_description"] = description
        adapted["Job Description"] = description

    # ========================================================
    # POSTED DATE / TIME
    # ========================================================

    posted_date = _first_value(
        raw,
        "posted_date",
        "posted_time",
        "posted",
        "Posted Date",
        "Posted Time",
    )

    if posted_date:

        adapted["posted_date"] = posted_date
        adapted["posted_time"] = posted_date
        adapted["posted"] = posted_date
        adapted["Posted Date"] = posted_date
        adapted["Posted Time"] = posted_date

    # ========================================================
    # EDUCATION
    # ========================================================

    education = _first_value(
        raw,
        "education",
        "qualification",
        "qualifications",
        "degree_required",
        "Education",
    )

    if education:

        adapted["education"] = education
        adapted["qualification"] = education
        adapted["qualifications"] = education
        adapted["degree_required"] = education
        adapted["Education"] = education

    # ========================================================
    # SKILLS
    # ========================================================

    skills = _first_value(
        raw,
        "skills",
        "skill",
        "Skills",
    )

    if skills:

        adapted["skills"] = skills
        adapted["skill"] = skills
        adapted["Skills"] = skills

    # ========================================================
    # JOB URL
    # ========================================================

    job_url = _first_value(
        raw,
        "job_url",
        "url",
        "link",
        "Job URL",
        "JobURL",
    )

    if job_url:

        adapted["job_url"] = job_url
        adapted["url"] = job_url
        adapted["link"] = job_url
        adapted["Job URL"] = job_url

    # ========================================================
    # JOB ID
    # ========================================================

    job_id = _first_value(
        raw,
        "job_id",
        "id",
        "Job ID",
        "jobId",
    )

    if job_id:

        adapted["job_id"] = job_id
        adapted["id"] = job_id
        adapted["Job ID"] = job_id

    # ========================================================
    # SEARCH KEYWORD
    # ========================================================

    search_keyword = _first_value(
        raw,
        "search_keyword",
        "search_keywords",
        "keyword",
        "query",
    )

    if search_keyword:

        adapted["search_keyword"] = (
            search_keyword
        )

        adapted["keyword"] = (
            search_keyword
        )

    return adapted


# ============================================================
# DEBUG RAW JOB
# ============================================================

def _debug_raw_job(
    source_key: str,
    raw: Any,
) -> None:
    """
    Display useful information when normalization fails.
    """

    if not isinstance(raw, dict):

        print(
            "[Normalization Warning] "
            f"{source_key}: scraper returned "
            f"non-dict record: "
            f"{type(raw).__name__}"
        )

        return

    title = _first_value(
        raw,
        "job_title",
        "title",
        "Job Title",
    )

    company = _first_value(
        raw,
        "company_name",
        "company",
        "Company Name",
    )

    location = _first_value(
        raw,
        "location",
        "locations",
        "Location",
        "Location(s)",
    )

    print(
        "[Normalization Warning] "
        f"{source_key}: invalid job -> "
        f"title='{title or NOT_SPECIFIED}', "
        f"company='{company or NOT_SPECIFIED}', "
        f"location='{location or NOT_SPECIFIED}'"
    )


# ============================================================
# NORMALIZE ONE SOURCE
# ============================================================

def _normalize_batch(
    source_key: str,
    raw_jobs: Iterable[dict],
    result: SourceResult,
) -> List[UnifiedJob]:
    """
    Normalize all jobs from one source.

    IMPORTANT:
        The current normalizer API is:

            normalize(raw_job)

        NOT:

            normalize(source_key, raw_job)
    """

    normalized: List[UnifiedJob] = []

    for index, raw in enumerate(
        raw_jobs,
        start=1,
    ):

        try:

            # ------------------------------------------------
            # Validate raw record
            # ------------------------------------------------

            if not isinstance(raw, dict):

                result.skipped_invalid += 1

                print(
                    "[Normalization Warning] "
                    f"{result.source} record #{index} "
                    f"is not a dictionary"
                )

                continue

            # ------------------------------------------------
            # ADAPT FIELD NAMES
            # ------------------------------------------------

            adapted = _adapt_source_job(
                source_key,
                raw,
            )

            # ------------------------------------------------
            # NORMALIZE
            #
            # IMPORTANT:
            #
            # normalize() determines the source from:
            #
            #     adapted["source"]
            #
            # ------------------------------------------------

            job = normalize(
                adapted
            )

            # ------------------------------------------------
            # SAFETY CHECK
            # ------------------------------------------------

            if job is None:

                result.skipped_invalid += 1

                _debug_raw_job(
                    source_key,
                    raw,
                )

                continue

            # ------------------------------------------------
            # BASIC UNIFIED JOB VALIDATION
            # ------------------------------------------------

            if not isinstance(
                job,
                UnifiedJob,
            ):

                result.skipped_invalid += 1

                print(
                    "[Normalization Warning] "
                    f"{result.source} record #{index} "
                    f"returned unexpected type: "
                    f"{type(job).__name__}"
                )

                continue

            if not _clean(
                getattr(
                    job,
                    "job_id",
                    "",
                )
            ):

                result.skipped_invalid += 1

                print(
                    "[Normalization Warning] "
                    f"{result.source} record #{index} "
                    f"has no job_id"
                )

                continue

            normalized.append(
                job
            )

        # ----------------------------------------------------
        # KNOWN PIPELINE ERRORS
        # ----------------------------------------------------

        except DataValidationError as error:

            result.skipped_invalid += 1

            print(
                "[Normalization Warning] "
                f"{result.source} record #{index}: "
                f"{error}"
            )

            _debug_raw_job(
                source_key,
                raw,
            )

        # ----------------------------------------------------
        # COMMON PYTHON DATA ERRORS
        # ----------------------------------------------------

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as error:

            result.skipped_invalid += 1

            print(
                "[Normalization Warning] "
                f"{result.source} record #{index}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            _debug_raw_job(
                source_key,
                raw,
            )

        # ----------------------------------------------------
        # UNEXPECTED ERROR
        # ----------------------------------------------------

        except Exception as error:

            result.skipped_invalid += 1

            print(
                "[Normalization Warning] "
                f"{result.source} record #{index}: "
                f"unexpected "
                f"{type(error).__name__}: "
                f"{error}"
            )

            _debug_raw_job(
                source_key,
                raw,
            )

    result.normalized = len(
        normalized
    )

    return normalized


# ============================================================
# DEDUPLICATION
# ============================================================

def _deduplicate_jobs(
    jobs: Iterable[UnifiedJob],
    seen_ids: set,
) -> List[UnifiedJob]:
    """
    Remove jobs already present in the persistent seen-ID set.

    Also removes duplicate IDs appearing within the same run.
    """

    fresh_jobs: List[UnifiedJob] = []

    batch_ids = set()

    for job in jobs:

        job_id = _clean(
            getattr(
                job,
                "job_id",
                "",
            )
        )

        if not job_id:
            continue

        # Existing database / CSV record
        if job_id in seen_ids:
            continue

        # Duplicate within current run
        if job_id in batch_ids:
            continue

        batch_ids.add(
            job_id
        )

        fresh_jobs.append(
            job
        )

    return fresh_jobs


# ============================================================
# ML ENRICHMENT
# ============================================================

def _enrich_jobs(
    source_name: str,
    jobs: Iterable[UnifiedJob],
) -> List[UnifiedJob]:
    """
    Run the existing enrichment layer.

    ml_predictor.py is NOT modified.
    """

    enriched_jobs = []

    for job in jobs:

        try:

            enriched_job = enrich_job(
                job
            )

            if enriched_job is None:

                # Never lose the original job because
                # enrichment returned None.
                enriched_job = job

            enriched_jobs.append(
                enriched_job
            )

        except Exception as error:

            print(
                "[Enrichment Warning] "
                f"{source_name}: "
                f"job_id="
                f"{getattr(job, 'job_id', 'unknown')} "
                f"enrichment failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            # Preserve original job.
            enriched_jobs.append(
                job
            )

    return enriched_jobs


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(
    store: JobStore,
    linkedin_collector: Optional[
        Callable[..., List[dict]]
    ] = None,
    linkedin_kwargs: Optional[dict] = None,
    naukri_collector: Optional[
        Callable[..., List[dict]]
    ] = None,
    naukri_kwargs: Optional[dict] = None,
    apply_enrichment: bool = True,
) -> RunReport:
    """
    Run LinkedIn and/or Naukri.

    Each source is isolated.

    If LinkedIn fails:
        Naukri continues.

    If Naukri fails:
        LinkedIn continues.

    Existing ML enrichment remains unchanged.
    """

    report = RunReport()

    # ========================================================
    # LOAD EXISTING SEEN IDS
    # ========================================================

    seen_ids = store.load_seen_ids()

    if seen_ids is None:
        seen_ids = set()

    # Safety conversion in case storage returns another
    # iterable type.
    seen_ids = set(
        seen_ids
    )

    all_new_jobs: List[
        UnifiedJob
    ] = []

    # ========================================================
    # BUILD SOURCE LIST
    # ========================================================

    sources = []

    if linkedin_collector is not None:

        sources.append(
            (
                "linkedin",
                "LinkedIn",
                linkedin_collector,
                linkedin_kwargs or {},
            )
        )

    if naukri_collector is not None:

        sources.append(
            (
                "naukri",
                "Naukri",
                naukri_collector,
                naukri_kwargs or {},
            )
        )

    if not sources:

        raise PipelineError(
            "run_pipeline was called "
            "with no collectors to run"
        )

    # ========================================================
    # PROCESS EACH SOURCE
    # ========================================================

    for (
        source_key,
        display_name,
        collector,
        kwargs,
    ) in sources:

        result = SourceResult(
            source=display_name
        )

        print()
        print("=" * 70)
        print(
            f"[Pipeline] Processing "
            f"{display_name}"
        )
        print("=" * 70)

        # ====================================================
        # SCRAPE
        # ====================================================

        try:

            raw_jobs = collector(
                **kwargs
            )

            if raw_jobs is None:
                raw_jobs = []

            raw_jobs = list(
                raw_jobs
            )

        except ScraperError as error:

            result.error = str(
                error
            )

            report.results.append(
                result
            )

            print(
                f"[Pipeline] "
                f"{display_name} scraping failed, "
                f"continuing with other sources: "
                f"{error}"
            )

            continue

        except Exception as error:

            result.error = (
                f"unexpected error: "
                f"{error}"
            )

            report.results.append(
                result
            )

            print(
                f"[Pipeline] "
                f"{display_name} raised an "
                f"unexpected error: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            continue

        # ====================================================
        # COLLECTION RESULT
        # ====================================================

        result.collected = len(
            raw_jobs
        )

        print(
            f"[Pipeline] "
            f"{display_name} collected "
            f"{result.collected} jobs"
        )

        # ====================================================
        # NORMALIZATION
        # ====================================================

        normalized_jobs = _normalize_batch(
            source_key,
            raw_jobs,
            result,
        )

        print(
            f"[Pipeline] "
            f"{display_name} normalized "
            f"{result.normalized} jobs"
        )

        print(
            f"[Pipeline] "
            f"{display_name} skipped "
            f"{result.skipped_invalid} invalid jobs"
        )

        # ====================================================
        # DEDUPLICATION
        # ====================================================

        fresh_jobs = _deduplicate_jobs(
            normalized_jobs,
            seen_ids,
        )

        print(
            f"[Pipeline] "
            f"{display_name} new jobs after "
            f"deduplication: "
            f"{len(fresh_jobs)}"
        )

        # ====================================================
        # ENRICHMENT
        # ====================================================

        if apply_enrichment and fresh_jobs:

            fresh_jobs = _enrich_jobs(
                display_name,
                fresh_jobs,
            )

            print(
                f"[Pipeline] "
                f"{display_name} enrichment complete"
            )

        elif not apply_enrichment:

            print(
                f"[Pipeline] "
                f"{display_name} enrichment disabled"
            )

        # ====================================================
        # ADD TO FINAL BATCH
        # ====================================================

        all_new_jobs.extend(
            fresh_jobs
        )

        # ====================================================
        # UPDATE SEEN IDS
        # ====================================================

        for job in fresh_jobs:

            job_id = _clean(
                getattr(
                    job,
                    "job_id",
                    "",
                )
            )

            if job_id:

                seen_ids.add(
                    job_id
                )

        # ====================================================
        # SAVE SOURCE RESULT
        # ====================================================

        report.results.append(
            result
        )

    # ========================================================
    # WRITE UNIFIED CSV
    # ========================================================

    print()
    print("=" * 70)
    print(
        "[Pipeline] Writing unified CSV"
    )
    print("=" * 70)

    if all_new_jobs:

        written = store.append_jobs(
            all_new_jobs
        )

    else:

        written = 0

    report.new_jobs_written = (
        written
    )

    # ========================================================
    # SAVE SEEN IDS
    # ========================================================

    # Save even when zero rows were written.
    #
    # This keeps the seen-ID state synchronized with the
    # current pipeline state.
    store.save_seen_ids(
        seen_ids
    )

    print(
        f"[Pipeline] "
        f"New rows written: "
        f"{written}"
    )

    return report


# ============================================================
# SIMPLE MODULE TEST
# ============================================================

def _run_orchestrator_tests():
    """
    Lightweight test for the source adapter.

    This does NOT run a scraper, database, or ML model.
    """

    print("=" * 70)
    print("ORCHESTRATOR MODULE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # LinkedIn adapter
    # --------------------------------------------------------

    linkedin_raw = {

        "job_title":
            "Data Analyst",

        "company_name":
            "Test Company",

        "location":
            "Hyderabad, Telangana, India",

        "job_description":
            "Test description",

        "posted_date":
            "2 hours ago",

        "education":
            r"B\.?E\., Bachelor(?:'s)?",

        "skills":
            "Python, SQL",

        "job_url":
            "https://example.com/job/1",

        "job_id":
            "linkedin_test_001",
    }

    linkedin_adapted = _adapt_source_job(
        "linkedin",
        linkedin_raw,
    )

    assert (
        linkedin_adapted["source"]
        == "LinkedIn"
    )

    assert (
        linkedin_adapted["title"]
        == "Data Analyst"
    )

    assert (
        linkedin_adapted["company"]
        == "Test Company"
    )

    assert (
        linkedin_adapted["location"]
        == "Hyderabad, Telangana, India"
    )

    assert (
        linkedin_adapted["job_id"]
        == "linkedin_test_001"
    )

    print(
        "[PASS] LinkedIn field adapter"
    )

    # --------------------------------------------------------
    # Naukri adapter
    # --------------------------------------------------------

    naukri_raw = {

        "title":
            "Business Analyst",

        "company":
            "Naukri Test Company",

        "Location":
            "Bengaluru, Karnataka, India",

        "description":
            "Test description",

        "posted_time":
            "Today",

        "qualification":
            "Bachelor's",

        "skill":
            "SQL, Excel",

        "url":
            "https://example.com/job/2",
    }

    naukri_adapted = _adapt_source_job(
        "naukri",
        naukri_raw,
    )

    assert (
        naukri_adapted["source"]
        == "Naukri"
    )

    assert (
        naukri_adapted["title"]
        == "Business Analyst"
    )

    assert (
        naukri_adapted["company"]
        == "Naukri Test Company"
    )

    assert (
        naukri_adapted["location"]
        == "Bengaluru, Karnataka, India"
    )

    print(
        "[PASS] Naukri field adapter"
    )

    # --------------------------------------------------------
    # Normalizer compatibility
    # --------------------------------------------------------

    linkedin_job = normalize(
        linkedin_adapted
    )

    assert isinstance(
        linkedin_job,
        UnifiedJob,
    )

    assert (
        linkedin_job.source
        == "LinkedIn"
    )

    assert (
        linkedin_job.city
        == "Hyderabad"
    )

    assert (
        linkedin_job.state
        == "Telangana"
    )

    assert (
        linkedin_job.country
        == "India"
    )

    print(
        "[PASS] Normalizer compatibility"
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "ORCHESTRATOR MODULE TEST PASSED"
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    _run_orchestrator_tests()