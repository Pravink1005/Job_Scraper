"""
Central configuration for the unified pipeline.

All common job-search keywords are controlled through SEARCH_KEYWORDS.

The same SEARCH_KEYWORDS list is used by:
    - LinkedIn
    - Naukri

Every setting has a sane default and can be overridden with an
environment variable (and therefore via a .env file).
"""

import os
from pathlib import Path


# ============================================================================
# OPTIONAL .env SUPPORT
# ============================================================================

try:
    from dotenv import load_dotenv

    load_dotenv()

except ImportError:
    # python-dotenv is optional.
    # Normal environment variables will still work.
    pass


# ============================================================================
# GENERAL PIPELINE SETTINGS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = Path(
    os.getenv(
        "PIPELINE_OUTPUT_DIR",
        BASE_DIR / "csv_output"
    )
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _csv_list(env_value, default):
    """
    Convert a comma-separated environment variable into a list.

    Example:
        DATA_ANALYST,DATA_SCIENTIST,BUSINESS_ANALYST

    becomes:

        [
            "DATA_ANALYST",
            "DATA_SCIENTIST",
            "BUSINESS_ANALYST"
        ]
    """

    if not env_value:
        return list(default)

    return [
        item.strip()
        for item in env_value.split(",")
        if item.strip()
    ]


def _int(env_value, default):
    """
    Safely convert an environment variable to integer.
    """

    try:
        return int(env_value) if env_value else default

    except (ValueError, TypeError):
        return default


def _bool(env_value, default):
    """
    Safely convert an environment variable to boolean.
    """

    if env_value is None:
        return default

    return env_value.strip().lower() in (
        "1",
        "true",
        "yes",
        "on"
    )


# ============================================================================
# COMMON JOB SEARCH KEYWORDS
# ============================================================================
#
# IMPORTANT:
# This is the MASTER keyword list.
#
# Change ONLY this list when you want to change the jobs being searched.
#
# Example:
#
# SEARCH_KEYWORDS = [
#     "data analyst",
#     "data scientist",
#     "business analyst",
# ]
#
# Both LinkedIn and Naukri will use the same keywords.
# ============================================================================

DEFAULT_SEARCH_KEYWORDS = [
    "Python developer","python engineer","python backend developer","python backend engineer",
]

# Environment variable priority:
#
# 1. SEARCH_KEYWORDS
# 2. LINKEDIN_KEYWORDS       (legacy compatibility)
# 3. NAUKRI_JOB_TITLES       (legacy compatibility)
# 4. DEFAULT_SEARCH_KEYWORDS
#
# This lets old .env files continue working while moving toward
# one centralized SEARCH_KEYWORDS setting.

SEARCH_KEYWORDS_ENV = (
    os.getenv("SEARCH_KEYWORDS")
    or os.getenv("LINKEDIN_KEYWORDS")
    or os.getenv("NAUKRI_JOB_TITLES")
)

SEARCH_KEYWORDS = _csv_list(
    SEARCH_KEYWORDS_ENV,
    DEFAULT_SEARCH_KEYWORDS,
)


# ============================================================================
# LINKEDIN SCRAPER SETTINGS
# ============================================================================

# Compatibility alias.
#
# Existing LinkedIn code can continue using LINKEDIN_KEYWORDS,
# but the actual values come from SEARCH_KEYWORDS.

LINKEDIN_KEYWORDS = list(
    SEARCH_KEYWORDS
)

LINKEDIN_LOCATION = os.getenv(
    "LINKEDIN_LOCATION",
    "India"
)

LINKEDIN_MAX_JOBS_PER_KEYWORD = _int(
    os.getenv("LINKEDIN_MAX_JOBS_PER_KEYWORD"),
    100
)

LINKEDIN_JOBS_PER_PAGE = _int(
    os.getenv("LINKEDIN_JOBS_PER_PAGE"),
    25
)

LINKEDIN_MAX_AGE_HOURS = _int(
    os.getenv("LINKEDIN_MAX_AGE_HOURS"),
    1
)


# ============================================================================
# NAUKRI SCRAPER SETTINGS
# ============================================================================

# Compatibility alias.
#
# Existing Naukri code can continue using NAUKRI_JOB_TITLES,
# but the actual values come from SEARCH_KEYWORDS.

NAUKRI_JOB_TITLES = list(
    SEARCH_KEYWORDS
)

NAUKRI_MAX_PAGES = _int(
    os.getenv("NAUKRI_MAX_PAGES"),
    5
)

NAUKRI_MAX_JOBS = _int(
    os.getenv("NAUKRI_MAX_JOBS"),
    100
)

NAUKRI_MAX_TOTAL = _int(
    os.getenv("NAUKRI_MAX_TOTAL"),
    None
)

try:
    NAUKRI_DELAY_SECONDS = float(
        os.getenv(
            "NAUKRI_DELAY_SECONDS",
            "2.0"
        )
    )

except (ValueError, TypeError):
    NAUKRI_DELAY_SECONDS = 2.0


NAUKRI_HEADLESS = _bool(
    os.getenv("NAUKRI_HEADLESS"),
    True
)

NAUKRI_BROWSER = os.getenv(
    "NAUKRI_BROWSER",
    "chromium"
)

NAUKRI_PROFILE_DIR = (
    os.getenv("NAUKRI_PROFILE_DIR")
    or None
)


# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

if __name__ == "__main__":

    print("=" * 72)
    print("PIPELINE CONFIGURATION")
    print("=" * 72)

    print()
    print("Search Keywords:")
    for index, keyword in enumerate(
        SEARCH_KEYWORDS,
        start=1
    ):
        print(f"  {index}. {keyword}")

    print()

    print("LinkedIn:")
    print(
        "  Keywords            :",
        LINKEDIN_KEYWORDS
    )
    print(
        "  Location            :",
        LINKEDIN_LOCATION
    )
    print(
        "  Max jobs/keyword    :",
        LINKEDIN_MAX_JOBS_PER_KEYWORD
    )
    print(
        "  Jobs/page           :",
        LINKEDIN_JOBS_PER_PAGE
    )
    print(
        "  Max age (hours)     :",
        LINKEDIN_MAX_AGE_HOURS
    )

    print()

    print("Naukri:")
    print(
        "  Job titles          :",
        NAUKRI_JOB_TITLES
    )
    print(
        "  Max pages           :",
        NAUKRI_MAX_PAGES
    )
    print(
        "  Max jobs/search     :",
        NAUKRI_MAX_JOBS
    )
    print(
        "  Max total           :",
        NAUKRI_MAX_TOTAL
    )
    print(
        "  Delay (seconds)     :",
        NAUKRI_DELAY_SECONDS
    )
    print(
        "  Headless            :",
        NAUKRI_HEADLESS
    )
    print(
        "  Browser             :",
        NAUKRI_BROWSER
    )
    print(
        "  Profile directory   :",
        NAUKRI_PROFILE_DIR
    )

    print()
    print(
        "Output directory:",
        OUTPUT_DIR
    )

    print("=" * 72)