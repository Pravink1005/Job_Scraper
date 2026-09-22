"""
Central configuration for the unified pipeline.

Every setting has a sane default matching the two original projects'
defaults, and every setting can be overridden with an environment variable
(and therefore via a `.env` file — see `.env.example`) so the combined
system can be configured without editing source code.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; if it's not installed, environment
    # variables set some other way (shell, CI, Docker) still work.
    pass

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("PIPELINE_OUTPUT_DIR", BASE_DIR / "csv_output"))


def _csv_list(env_value, default):
    if not env_value:
        return default
    return [item.strip() for item in env_value.split(",") if item.strip()]


def _int(env_value, default):
    try:
        return int(env_value) if env_value else default
    except ValueError:
        return default


def _bool(env_value, default):
    if env_value is None:
        return default
    return env_value.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# LinkedIn scraper settings
# ---------------------------------------------------------------------------

LINKEDIN_KEYWORDS = _csv_list(
    os.getenv("LINKEDIN_KEYWORDS"),
    ["Python Full Stack Developer", "Python Backend Developer", "SQL Developer"],
)
LINKEDIN_LOCATION = os.getenv("LINKEDIN_LOCATION", "India")
LINKEDIN_MAX_JOBS_PER_KEYWORD = _int(os.getenv("LINKEDIN_MAX_JOBS_PER_KEYWORD"), 100)
LINKEDIN_JOBS_PER_PAGE = _int(os.getenv("LINKEDIN_JOBS_PER_PAGE"), 25)
LINKEDIN_MAX_AGE_HOURS = _int(os.getenv("LINKEDIN_MAX_AGE_HOURS"), 1)

# ---------------------------------------------------------------------------
# Naukri scraper settings
# ---------------------------------------------------------------------------

NAUKRI_JOB_TITLES = _csv_list(os.getenv("NAUKRI_JOB_TITLES"), ["data analyst"])
NAUKRI_MAX_PAGES = _int(os.getenv("NAUKRI_MAX_PAGES"), 5)
NAUKRI_MAX_JOBS = _int(os.getenv("NAUKRI_MAX_JOBS"), 100)
NAUKRI_MAX_TOTAL = _int(os.getenv("NAUKRI_MAX_TOTAL"), None)
NAUKRI_DELAY_SECONDS = float(os.getenv("NAUKRI_DELAY_SECONDS", "2.0"))
NAUKRI_HEADLESS = _bool(os.getenv("NAUKRI_HEADLESS"), True)
NAUKRI_BROWSER = os.getenv("NAUKRI_BROWSER", "chromium")
NAUKRI_PROFILE_DIR = os.getenv("NAUKRI_PROFILE_DIR") or None
