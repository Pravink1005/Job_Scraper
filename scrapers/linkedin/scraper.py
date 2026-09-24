# ============================================================
# LinkedIn Job Scraper
# Production / Stable Version
# ============================================================

import os
import re
import time
import random
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )


# ============================================================
# SCRAPLING
# ============================================================

try:
    from scrapling import Fetcher
except ImportError:
    Fetcher = None


# ============================================================
# CONSTANTS
# ============================================================

BASE_URL = "https://www.linkedin.com"

NOT_SPECIFIED = "Not specified"


# ------------------------------------------------------------
# DEFAULT LINKEDIN TIME WINDOW
#
# Can be changed through environment variable:
#
# LINKEDIN_MAX_AGE_HOURS=1
# LINKEDIN_MAX_AGE_HOURS=4
# LINKEDIN_MAX_AGE_HOURS=24
#
# Default = 24 hours
# ------------------------------------------------------------

DEFAULT_MAX_AGE_HOURS = float(
    os.getenv(
        "LINKEDIN_MAX_AGE_HOURS",
        "24"
    )
)


DEFAULT_MAX_JOBS = int(
    os.getenv(
        "LINKEDIN_MAX_JOBS",
        "100"
    )
)


DEFAULT_JOBS_PER_PAGE = int(
    os.getenv(
        "LINKEDIN_JOBS_PER_PAGE",
        "25"
    )
)


MIN_DELAY = float(
    os.getenv(
        "LINKEDIN_DELAY_MIN",
        "2"
    )
)


MAX_DELAY = float(
    os.getenv(
        "LINKEDIN_DELAY_MAX",
        "4"
    )
)


MAX_PAGES = int(
    os.getenv(
        "LINKEDIN_MAX_PAGES",
        "4"
    )
)


# ============================================================
# FETCHER
# ============================================================

_fetcher = None


def get_fetcher():

    global _fetcher

    if _fetcher is not None:
        return _fetcher

    if Fetcher is None:
        raise ImportError(
            "Scrapling is not installed.\n"
            "Run:\n"
            "pip install scrapling"
        )

    _fetcher = Fetcher()

    return _fetcher


# ============================================================
# SAFE FETCH
# ============================================================

def safe_fetch_get(
    url,
    timeout=30
):

    fetcher = get_fetcher()

    try:

        response = fetcher.get(
            url,
            timeout=timeout,
            follow_redirects=False
        )

        actual_url = getattr(
            response,
            "url",
            None
        )

        if actual_url:

            logger.info(
                "Requested URL : %s",
                url
            )

            logger.info(
                "Fetched URL   : %s",
                actual_url
            )

        return response

    except TypeError:

        try:

            response = fetcher.get(
                url
            )

            actual_url = getattr(
                response,
                "url",
                None
            )

            if actual_url:

                logger.info(
                    "Requested URL : %s",
                    url
                )

                logger.info(
                    "Fetched URL   : %s",
                    actual_url
                )

            return response

        except Exception as exc:

            logger.error(
                "Fetch failed: %s",
                exc
            )

            return None

    except Exception as exc:

        logger.error(
            "Fetch failed: %s",
            exc
        )

        return None


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(
    value
):

    if value is None:
        return ""

    try:
        value = str(value)
    except Exception:
        return ""

    value = value.replace(
        "\xa0",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def element_text(
    element
):

    if element is None:
        return ""

    try:

        values = element.css(
            "::text"
        ).getall()

        text = " ".join(
            clean_text(value)
            for value in values
            if clean_text(value)
        )

        if text:
            return clean_text(text)

    except Exception:
        pass

    try:

        text = clean_text(
            element.text
        )

        if text:
            return text

    except Exception:
        pass

    return ""


def get_attribute(
    element,
    name
):

    if element is None:
        return ""

    try:

        return clean_text(
            element.attrib.get(
                name,
                ""
            )
        )

    except Exception:
        return ""


def first_element(
    container,
    selectors
):

    for selector in selectors:

        try:

            elements = container.css(
                selector
            )

            if elements:
                return elements[0]

        except Exception:
            continue

    return None


def first_text(
    container,
    selectors
):

    for selector in selectors:

        try:

            elements = container.css(
                selector
            )

            for element in elements:

                text = element_text(
                    element
                )

                if text:
                    return text

        except Exception:
            continue

    return ""


# ============================================================
# LINKEDIN LOCATION VALIDATION
# ============================================================

LINKEDIN_LOCATION_BAD_MARKERS = [

    "minutes ago",
    "minute ago",

    "hours ago",
    "hour ago",

    "days ago",
    "day ago",

    "weeks ago",
    "week ago",

    "applicants",
    "applicant",

    "see who",

    "has hired",

]


def is_clean_linkedin_location(
    value,
    company=""
):

    value = clean_text(
        value
    )

    if not value:
        return False

    lower_value = value.lower()

    # --------------------------------------------------------
    # Reject LinkedIn metadata
    # --------------------------------------------------------

    for marker in LINKEDIN_LOCATION_BAD_MARKERS:

        if marker in lower_value:
            return False

    # --------------------------------------------------------
    # Reject obvious company contamination
    # --------------------------------------------------------

    company = clean_text(
        company
    )

    if company:

        company_lower = company.lower()

        if (
            company_lower in lower_value
            and len(value) > len(company) + 10
        ):

            return False

    return True


# ============================================================
# POSTED DATE PARSING
# ============================================================

def parse_relative_posted_text(
    text
):

    text = clean_text(
        text
    ).lower()

    if not text:
        return None

    now = datetime.now()

    # --------------------------------------------------------
    # Seconds
    # --------------------------------------------------------

    match = re.search(
        r"(\d+)\s*seconds?\s*ago",
        text
    )

    if match:

        return (
            now
            - timedelta(
                seconds=int(
                    match.group(1)
                )
            )
        )

    # --------------------------------------------------------
    # Minutes
    # --------------------------------------------------------

    match = re.search(
        r"(\d+)\s*minutes?\s*ago",
        text
    )

    if match:

        return (
            now
            - timedelta(
                minutes=int(
                    match.group(1)
                )
            )
        )

    # --------------------------------------------------------
    # Hours
    # --------------------------------------------------------

    match = re.search(
        r"(\d+)\s*hours?\s*ago",
        text
    )

    if match:

        return (
            now
            - timedelta(
                hours=int(
                    match.group(1)
                )
            )
        )

    # --------------------------------------------------------
    # One hour
    # --------------------------------------------------------

    if (
        "an hour ago" in text
        or "1 hour ago" in text
    ):

        return (
            now
            - timedelta(
                hours=1
            )
        )

    # --------------------------------------------------------
    # Today
    # --------------------------------------------------------

    if text == "today":

        return now

    # --------------------------------------------------------
    # Yesterday
    # --------------------------------------------------------

    if "yesterday" in text:

        return (
            now
            - timedelta(
                days=1
            )
        )

    # --------------------------------------------------------
    # Days
    # --------------------------------------------------------

    match = re.search(
        r"(\d+)\s*days?\s*ago",
        text
    )

    if match:

        return (
            now
            - timedelta(
                days=int(
                    match.group(1)
                )
            )
        )

    # --------------------------------------------------------
    # Weeks
    # --------------------------------------------------------

    match = re.search(
        r"(\d+)\s*weeks?\s*ago",
        text
    )

    if match:

        return (
            now
            - timedelta(
                weeks=int(
                    match.group(1)
                )
            )
        )

    return None


def parse_absolute_datetime(
    value
):

    value = clean_text(
        value
    )

    if not value:
        return None

    formats = [

        "%Y-%m-%d %H:%M:%S",

        "%Y-%m-%d %H:%M",

        "%d-%m-%Y %H:%M:%S",

        "%d-%m-%Y %H:%M",

        "%d/%m/%Y %H:%M:%S",

        "%d/%m/%Y %H:%M",

        "%Y/%m/%d %H:%M:%S",

        "%Y/%m/%d %H:%M",

    ]

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is not None:

            parsed = parsed.replace(
                tzinfo=None
            )

        return parsed

    except Exception:
        pass

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            )

        except Exception:
            continue

    return None


def extract_posted_time(
    card
):

    selectors = [

        "time",

        ".base-search-card__listdate",

        ".job-search-card__listdate",

        "span[class*='listdate']",

        "span[class*='posted']",

        "div[class*='listdate']",

        "div[class*='posted']",

    ]

    # --------------------------------------------------------
    # Visible relative time
    # --------------------------------------------------------

    for selector in selectors:

        try:

            elements = card.css(
                selector
            )

        except Exception:

            continue

        for element in elements:

            visible_text = element_text(
                element
            )

            if not visible_text:
                continue

            parsed = parse_relative_posted_text(
                visible_text
            )

            if parsed:

                return parsed.strftime(
                    "%d-%m-%Y %H:%M"
                )

    # --------------------------------------------------------
    # Complete card text
    # --------------------------------------------------------

    try:

        complete_text = element_text(
            card
        )

        parsed = parse_relative_posted_text(
            complete_text
        )

        if parsed:

            return parsed.strftime(
                "%d-%m-%Y %H:%M"
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # datetime attribute
    # --------------------------------------------------------

    for selector in selectors:

        try:

            elements = card.css(
                selector
            )

        except Exception:

            continue

        for element in elements:

            datetime_value = get_attribute(
                element,
                "datetime"
            )

            if not datetime_value:
                continue

            parsed = parse_absolute_datetime(
                datetime_value
            )

            if parsed:

                return parsed.strftime(
                    "%d-%m-%Y %H:%M"
                )

    return NOT_SPECIFIED


def is_recent_posted_time(
    posted_date,
    max_age_hours
):

    if not posted_date:
        return True

    posted_date = clean_text(
        posted_date
    )

    if posted_date == NOT_SPECIFIED:
        return True

    parsed = parse_absolute_datetime(
        posted_date
    )

    if parsed is None:
        return True

    age = (
        datetime.now()
        - parsed
    )

    if age.total_seconds() < 0:
        return True

    return (
        age.total_seconds()
        <= (
            float(max_age_hours)
            * 3600
        )
    )


# ============================================================
# SEARCH URL
# ============================================================

def build_search_url(
    keyword,
    location,
    start,
    max_age_hours
):

    age_seconds = int(
        float(max_age_hours)
        * 3600
    )

    return (
        "https://www.linkedin.com/jobs/search/"
        "?keywords="
        + quote_plus(keyword)
        + "&location="
        + quote_plus(location)
        + "&f_TPR=r"
        + str(age_seconds)
        + "&start="
        + str(start)
    )


# ============================================================
# FIND JOB CARDS
# ============================================================

def find_job_cards(
    response
):

    selectors = [

        "li div.base-card",

        "li.base-card",

        "li div.base-search-card",

        "li.base-search-card",

        ".base-card",

        ".base-search-card",

        ".job-search-card",

    ]

    for selector in selectors:

        try:

            cards = response.css(
                selector
            )

            if cards:

                logger.info(
                    "LinkedIn selector '%s' found %d job cards",
                    selector,
                    len(cards)
                )

                return list(cards)

        except Exception:
            continue

    return []


# ============================================================
# TITLE
# ============================================================

def extract_title(
    card
):

    selectors = [

        "h3.base-search-card__title",

        "h3.base-card__full-link",

        "h3",

        "[class*='job-title']",

        "[class*='title']",

    ]

    value = first_text(
        card,
        selectors
    )

    return (
        value
        if value
        else NOT_SPECIFIED
    )


# ============================================================
# COMPANY
# ============================================================

def extract_company(
    card
):

    selectors = [

        "h4.base-search-card__subtitle",

        "h4.base-card__subtitle",

        "a[href*='/company/']",

        "h4",

        "[class*='company-name']",

        "[class*='subtitle']",

    ]

    bad_markers = [

        "minutes ago",
        "minute ago",

        "hours ago",
        "hour ago",

        "days ago",
        "day ago",

        "applicants",
        "applicant",

        "see who",

        "has hired for this role",

    ]

    for selector in selectors:

        try:

            elements = card.css(
                selector
            )

        except Exception:

            continue

        for element in elements:

            value = element_text(
                element
            )

            if not value:
                continue

            lower_value = value.lower()

            if any(
                marker in lower_value
                for marker in bad_markers
            ):

                continue

            return value

    return NOT_SPECIFIED


# ============================================================
# LOCATION
# ============================================================

def extract_location(
    card
):

    selectors = [

        ".job-search-card__location",

        "span.job-search-card__location",

        ".base-search-card__metadata .job-search-card__location",

        "span[class*='job-search-card__location']",

        "span[class*='location']",

    ]

    for selector in selectors:

        try:

            elements = card.css(
                selector
            )

        except Exception:

            continue

        for element in elements:

            value = element_text(
                element
            )

            if not value:
                continue

            if is_clean_linkedin_location(
                value
            ):

                return value

    # --------------------------------------------------------
    # Fallback: inspect individual metadata spans
    # --------------------------------------------------------

    metadata_selectors = [

        ".base-search-card__metadata",

        ".base-card__metadata",

    ]

    for selector in metadata_selectors:

        try:

            containers = card.css(
                selector
            )

        except Exception:

            continue

        for container in containers:

            try:

                children = container.css(
                    "span"
                )

            except Exception:

                children = []

            for child in children:

                value = element_text(
                    child
                )

                if not value:
                    continue

                if is_clean_linkedin_location(
                    value
                ):

                    return value

    return NOT_SPECIFIED


# ============================================================
# JOB URL
# ============================================================

def extract_job_url(
    card
):

    selectors = [

        "a.base-card__full-link",

        "a.base-search-card__full-link",

        "a[href*='/jobs/view/']",

    ]

    element = first_element(
        card,
        selectors
    )

    if element is None:
        return NOT_SPECIFIED

    href = get_attribute(
        element,
        "href"
    )

    if not href:
        return NOT_SPECIFIED

    if href.startswith(
        "https://"
    ):

        url = href

    elif href.startswith(
        "http://"
    ):

        url = href

    elif href.startswith(
        "/"
    ):

        url = (
            BASE_URL
            + href
        )

    else:

        url = (
            BASE_URL
            + "/"
            + href
        )

    parsed = urlparse(
        url
    )

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            "",
            ""
        )
    )


# ============================================================
# CARD EXTRACTION
# ============================================================

def extract_job_from_card(
    card,
    keyword
):

    return {

        "job_title": extract_title(
            card
        ),

        "company_name": extract_company(
            card
        ),

        "location": extract_location(
            card
        ),

        "job_description": NOT_SPECIFIED,

        "posted_date": extract_posted_time(
            card
        ),

        "education": NOT_SPECIFIED,

        "skills": NOT_SPECIFIED,

        "job_url": extract_job_url(
            card
        ),

        "source": "LinkedIn",

        "search_keyword": keyword,

    }


# ============================================================
# DETAIL DESCRIPTION
# ============================================================

def extract_description(
    page
):

    selectors = [

        ".show-more-less-html__markup",

        ".description__text",

        "section.description",

        "div[class*='description']",

        "[class*='job-description']",

    ]

    for selector in selectors:

        try:

            elements = page.css(
                selector
            )

        except Exception:

            continue

        if not elements:
            continue

        texts = []

        for element in elements:

            text = element_text(
                element
            )

            if text:
                texts.append(
                    text
                )

        if texts:

            return "\n".join(
                dict.fromkeys(
                    texts
                )
            )

    return NOT_SPECIFIED


# ============================================================
# DETAIL COMPANY
# ============================================================

def extract_detail_company(
    page
):

    selectors = [

        ".topcard__org-name-link",

        ".top-card-layout__card a[href*='/company/']",

        "a[href*='/company/']",

    ]

    value = first_text(
        page,
        selectors
    )

    if not value:
        return NOT_SPECIFIED

    bad_markers = [

        "minutes ago",
        "minute ago",

        "hours ago",
        "hour ago",

        "applicants",
        "applicant",

        "see who",

        "has hired for this role",

    ]

    if any(
        marker in value.lower()
        for marker in bad_markers
    ):

        return NOT_SPECIFIED

    return value


# ============================================================
# DETAIL LOCATION
# ============================================================

def extract_detail_location(
    page
):

    selectors = [

        ".topcard__flavor--bullet",

        ".top-card-layout__second-subline .topcard__flavor",

        ".top-card-layout__second-subline .topcard__flavor--bullet",

    ]

    candidates = []

    for selector in selectors:

        try:

            elements = page.css(
                selector
            )

        except Exception:
            continue

        for element in elements:

            value = element_text(
                element
            )

            if not value:
                continue

            value = clean_text(
                value
            )

            lower_value = value.lower()

            bad_values = [

                "clear text",

                "see who",

                "has hired",

                "applicants",

                "applicant",

                "minutes ago",

                "minute ago",

                "hours ago",

                "hour ago",

                "days ago",

                "day ago",

                "weeks ago",

                "week ago",

                "full-time",

                "part-time",

                "contract",

                "internship",

                "remote",

                "hybrid",

            ]

            if any(
                bad in lower_value
                for bad in bad_values
            ):

                continue

            company = clean_text(
                extract_detail_company(
                    page
                )
            )

            if company:

                if (
                    lower_value
                    == company.lower()
                ):

                    continue

            if len(value) < 3:
                continue

            location_indicators = [

                "india",
                "united states",
                "usa",
                "united kingdom",
                "uk",
                "canada",
                "australia",

                "bengaluru",
                "bangalore",
                "hyderabad",
                "chennai",
                "mumbai",
                "pune",
                "delhi",
                "gurugram",
                "gurgaon",
                "noida",
                "kolkata",
                "coimbatore",
                "ahmedabad",
                "jaipur",
                "kochi",

                "karnataka",
                "telangana",
                "tamil nadu",
                "maharashtra",
                "kerala",
                "west bengal",
                "gujarat",
                "haryana",
                "uttar pradesh",

                "remote",

            ]

            has_location_indicator = any(
                indicator in lower_value
                for indicator in location_indicators
            )

            has_location_structure = (
                "," in value
            )

            if (
                has_location_indicator
                or has_location_structure
            ):

                if value not in candidates:

                    candidates.append(
                        value
                    )

    if candidates:

        return candidates[0]

    return NOT_SPECIFIED


# ============================================================
# EDUCATION
# ============================================================

def extract_education(
    description
):

    if not description:
        return NOT_SPECIFIED

    text = clean_text(
        description
    )

    found = []

    patterns = [

        (
            r"\bB\.?\s*E\.?\b",
            "B.E."
        ),

        (
            r"\bB\.?\s*Tech\b",
            "B.Tech"
        ),

        (
            r"\bB\.?\s*Sc\.?\b",
            "B.Sc."
        ),

        (
            r"\bB\.?\s*A\.?\b",
            "B.A."
        ),

        (
            r"\bM\.?\s*E\.?\b",
            "M.E."
        ),

        (
            r"\bM\.?\s*Tech\b",
            "M.Tech"
        ),

        (
            r"\bM\.?\s*Sc\.?\b",
            "M.Sc."
        ),

        (
            r"\bM\.?\s*A\.?\b",
            "M.A."
        ),

        (
            r"\bMBA\b",
            "MBA"
        ),

        (
            r"\bBachelor(?:'s)?\b",
            "Bachelor's"
        ),

        (
            r"\bMaster(?:'s)?\b",
            "Master's"
        ),

        (
            r"\bPh\.?D\.?\b",
            "Ph.D."
        ),

    ]

    for pattern, label in patterns:

        try:

            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):

                if label not in found:

                    found.append(
                        label
                    )

        except Exception:
            continue

    if not found:

        return NOT_SPECIFIED

    return ", ".join(
        found
    )


# ============================================================
# SKILLS
# ============================================================

COMMON_SKILLS = [

    "Python",
    "R",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "Excel",
    "Power BI",
    "Tableau",
    "Power Query",
    "DAX",
    "Pandas",
    "NumPy",
    "Matplotlib",
    "Seaborn",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Keras",
    "XGBoost",
    "LightGBM",
    "Machine Learning",
    "Deep Learning",
    "Artificial Intelligence",
    "NLP",
    "OpenCV",
    "YOLO",
    "AWS",
    "Azure",
    "Google Cloud",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "GitHub",
    "Jira",
    "Spark",
    "Hadoop",
    "ETL",
    "Data Analysis",
    "Data Visualization",
    "Statistics",
    "Streamlit",
    "Java",
    "JavaScript",
    "C++",
    "C#",
    "HTML",
    "CSS",
    "FastAPI",
    "Flask",
    "Django",

]


def extract_skills(
    description
):

    if not description:
        return NOT_SPECIFIED

    description_lower = description.lower()

    def has_r_language_context() -> bool:
        patterns = [
            r"\br\s+(?:programming|language)\b",
            r"\brstudio\b",
            r"\busing\s+r\b",
            r"\bexperience\s+with\s+r\b",
            r"\bskills?\s*:[^.;]{0,120}\br\b",
            r"\br\s*/\s*(?:python|sql)\b",
            r"\b(?:python|sql)\s*/\s*r\b",
            r"\br\s*,\s*(?:python|sql)\b",
            r"\b(?:python|sql)\s*,\s*r\b",
        ]

        return any(
            re.search(
                pattern,
                description_lower,
                flags=re.I,
            )
            for pattern in patterns
        )

    found = []

    for skill in COMMON_SKILLS:

        if skill == "R":
            if not has_r_language_context():
                continue

            found.append(skill)
            continue

        if re.search(
            rf"(?<![A-Za-z0-9]){re.escape(skill.lower())}(?![A-Za-z0-9])",
            description_lower,
            flags=re.I,
        ):

            found.append(
                skill
            )

    if not found:
        return NOT_SPECIFIED

    return ", ".join(
        found
    )


# ============================================================
# DETAIL PAGE ENRICHMENT
# ============================================================

def enrich_job(
    job
):

    url = job.get(
        "job_url"
    )

    if (
        not url
        or url == NOT_SPECIFIED
    ):

        return job

    logger.info(
        "Fetching detail: %s",
        job.get(
            "job_title"
        )
    )

    try:

        response = safe_fetch_get(
            url,
            timeout=30
        )

        if response is None:
            return job

        status = getattr(
            response,
            "status_code",
            None
        )

        if (
            status is not None
            and status >= 400
        ):

            logger.warning(
                "Detail page returned HTTP %s",
                status
            )

            return job

        # ----------------------------------------------------
        # Description
        # ----------------------------------------------------

        description = extract_description(
            response
        )

        if description != NOT_SPECIFIED:

            job[
                "job_description"
            ] = description

        # ----------------------------------------------------
        # Company
        # ----------------------------------------------------

        company = extract_detail_company(
            response
        )

        if company != NOT_SPECIFIED:

            job[
                "company_name"
            ] = company

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location = extract_detail_location(
            response
        )

        if (
            location != NOT_SPECIFIED
            and is_clean_linkedin_location(
                location,
                job.get(
                    "company_name",
                    ""
                )
            )
        ):

            job[
                "location"
            ] = location

        # ----------------------------------------------------
        # Education
        # ----------------------------------------------------

        job[
            "education"
        ] = extract_education(
            job.get(
                "job_description",
                ""
            )
        )

        # ----------------------------------------------------
        # Skills
        # ----------------------------------------------------

        job[
            "skills"
        ] = extract_skills(
            job.get(
                "job_description",
                ""
            )
        )

    except Exception as exc:

        logger.warning(
            "Detail extraction failed: %s",
            exc
        )

    return job


# ============================================================
# EXISTING ML PREDICTOR
# ============================================================

def apply_existing_ml_predictor(
    job
):

    try:

        import ml_predictor

    except Exception:

        return job

    possible_functions = [

        "predict_job",
        "predict",
        "predict_score",
        "enrich_job",
        "process_job",

    ]

    for function_name in possible_functions:

        function = getattr(
            ml_predictor,
            function_name,
            None
        )

        if not callable(
            function
        ):

            continue

        try:

            result = function(
                job
            )

            if isinstance(
                result,
                dict
            ):

                job.update(
                    result
                )

            return job

        except TypeError:

            continue

        except Exception as exc:

            logger.warning(
                "ML predictor error: %s",
                exc
            )

            return job

    return job


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_job(
    job
):

    fields = [

        "job_title",
        "company_name",
        "location",
        "job_description",
        "posted_date",
        "education",
        "skills",
        "job_url",
        "source",

    ]

    for field in fields:

        value = clean_text(
            job.get(
                field,
                ""
            )
        )

        if not value:

            value = NOT_SPECIFIED

        job[field] = value

    return job


# ============================================================
# SCRAPE SEARCH PAGE
# ============================================================

def scrape_search_page(
    keyword,
    location,
    start,
    max_age_hours
):

    url = build_search_url(
        keyword,
        location,
        start,
        max_age_hours
    )

    logger.info(
        "Loading LinkedIn page: start=%s",
        start
    )

    logger.info(
        "URL: %s",
        url
    )

    response = safe_fetch_get(
        url
    )

    if response is None:

        return (
            [],
            False
        )

    status = getattr(
        response,
        "status_code",
        None
    )

    if status:

        logger.info(
            "LinkedIn HTTP status: %s",
            status
        )

    if status == 429:

        logger.warning(
            "LinkedIn returned HTTP 429."
        )

        return (
            [],
            False
        )

    if (
        status is not None
        and status >= 400
    ):

        logger.warning(
            "LinkedIn returned HTTP %s",
            status
        )

        return (
            [],
            False
        )

    cards = find_job_cards(
        response
    )

    if not cards:

        logger.warning(
            "No LinkedIn job cards found."
        )

        return (
            [],
            True
        )

    jobs = []

    for card in cards:

        try:

            job = extract_job_from_card(
                card,
                keyword
            )

            if (
                not job.get(
                    "job_url"
                )
                or job[
                    "job_url"
                ] == NOT_SPECIFIED
            ):

                continue

            if not is_recent_posted_time(
                job.get(
                    "posted_date"
                ),
                max_age_hours
            ):

                logger.info(
                    "Skipping old job: %s | %s",
                    job.get(
                        "job_title"
                    ),
                    job.get(
                        "posted_date"
                    )
                )

                continue

            logger.info(
                "Queued job: %s | %s | %s",
                job.get(
                    "job_title"
                ),
                job.get(
                    "company_name"
                ),
                job.get(
                    "location"
                )
            )

            jobs.append(
                job
            )

        except Exception as exc:

            logger.warning(
                "LinkedIn card extraction failed: %s",
                exc
            )

    return (
        jobs,
        True
    )


# ============================================================
# MAIN PUBLIC FUNCTION
# ============================================================

# ============================================================
# MAIN PUBLIC FUNCTION
# ============================================================

def collect_linkedin_jobs(
    keywords=None,
    location=None,
    search_keywords=None,
    max_jobs_per_keyword=DEFAULT_MAX_JOBS,
    jobs_per_page=DEFAULT_JOBS_PER_PAGE,
    max_age_hours=DEFAULT_MAX_AGE_HOURS,
    enable_detail_pages=True,
    enable_ml=True,
    **kwargs
):

    # ========================================================
    # MAX JOBS COMPATIBILITY
    # ========================================================

    if "max_jobs" in kwargs and kwargs["max_jobs"] is not None:
        max_jobs_per_keyword = kwargs["max_jobs"]

    # ========================================================
    # KEYWORDS
    # ========================================================

    if keywords is None:
        keywords = search_keywords

    if keywords is None:
        keywords = kwargs.get(
            "keyword_list"
        )

    if isinstance(keywords, str):
        keywords = [
            keywords
        ]

    if not keywords:
        keywords = [
            "data analyst"
        ]

    # ========================================================
    # LOCATION
    # ========================================================

    if location is None:
        location = kwargs.get(
            "search_location"
        )

    if not location:
        location = "India"

    # ========================================================
    # NORMALIZE CONFIGURATION
    # ========================================================

    try:
        max_jobs_per_keyword = max(
            1,
            int(max_jobs_per_keyword)
        )
    except Exception:
        max_jobs_per_keyword = DEFAULT_MAX_JOBS

    try:
        jobs_per_page = max(
            1,
            int(jobs_per_page)
        )
    except Exception:
        jobs_per_page = DEFAULT_JOBS_PER_PAGE

    try:
        max_age_hours = max(
            0.01,
            float(max_age_hours)
        )
    except Exception:
        max_age_hours = DEFAULT_MAX_AGE_HOURS

    # ========================================================
    # LOG CONFIGURATION
    # ========================================================

    logger.info(
        "=" * 72
    )

    logger.info(
        "LINKEDIN JOB COLLECTION STARTED"
    )

    logger.info(
        "Keywords       : %s",
        keywords
    )

    logger.info(
        "Location       : %s",
        location
    )

    logger.info(
        "Max jobs/keyword: %s",
        max_jobs_per_keyword
    )

    logger.info(
        "Jobs per page  : %s",
        jobs_per_page
    )

    logger.info(
        "Max age hours  : %s",
        max_age_hours
    )

    logger.info(
        "TPR seconds    : %s",
        int(max_age_hours * 3600)
    )

    logger.info(
        "Detail pages   : %s",
        enable_detail_pages
    )

    logger.info(
        "ML enrichment  : %s",
        enable_ml
    )

    logger.info(
        "=" * 72
    )

    # ========================================================
    # COLLECTION
    # ========================================================

    all_jobs = []

    # Keep URLs unique across keywords/pages
    seen_urls = set()

    # ========================================================
    # PROCESS EACH KEYWORD
    # ========================================================

    for keyword in keywords:

        keyword = clean_text(
            keyword
        )

        if not keyword:
            continue

        logger.info(
            "=" * 72
        )

        logger.info(
            "Processing LinkedIn keyword: %s",
            keyword
        )

        logger.info(
            "=" * 72
        )

        keyword_jobs = []

        # ----------------------------------------------------
        # PAGINATION
        # ----------------------------------------------------

        for start in range(
            0,
            max_jobs_per_keyword,
            jobs_per_page
        ):

            page_number = (
                start // jobs_per_page
            ) + 1

            if page_number > MAX_PAGES:

                logger.info(
                    "Reached MAX_PAGES=%s",
                    MAX_PAGES
                )

                break

            logger.info(
                "LinkedIn page %s | start=%s | keyword=%s",
                page_number,
                start,
                keyword
            )

            try:

                jobs, request_ok = scrape_search_page(
                    keyword=keyword,
                    location=location,
                    start=start,
                    max_age_hours=max_age_hours
                )

            except Exception as exc:

                logger.error(
                    "LinkedIn search page failed: %s",
                    exc
                )

                break

            if not request_ok:

                logger.warning(
                    "LinkedIn request failed at start=%s",
                    start
                )

                break

            if not jobs:

                logger.info(
                    "No jobs returned for start=%s",
                    start
                )

                break

            page_new = 0

            # ------------------------------------------------
            # PROCESS PAGE JOBS
            # ------------------------------------------------

            for job in jobs:

                job_url = clean_text(
                    job.get(
                        "job_url",
                        ""
                    )
                )

                if not job_url:
                    continue

                if job_url == NOT_SPECIFIED:
                    continue

                # --------------------------------------------
                # GLOBAL URL DEDUPLICATION
                # --------------------------------------------

                if job_url in seen_urls:

                    logger.info(
                        "Skipping duplicate job: %s",
                        job_url
                    )

                    continue

                seen_urls.add(
                    job_url
                )

                # --------------------------------------------
                # ADD JOB
                # --------------------------------------------

                keyword_jobs.append(
                    job
                )

                all_jobs.append(
                    job
                )

                page_new += 1

                logger.info(
                    "Accepted LinkedIn job %s/%s: %s",
                    len(keyword_jobs),
                    max_jobs_per_keyword,
                    job.get(
                        "job_title"
                    )
                )

                # --------------------------------------------
                # STRICT MAX JOB LIMIT
                # --------------------------------------------

                if (
                    len(keyword_jobs)
                    >= max_jobs_per_keyword
                ):

                    break

            logger.info(
                "Page %s completed | cards accepted=%s | keyword total=%s/%s",
                page_number,
                page_new,
                len(keyword_jobs),
                max_jobs_per_keyword
            )

            # ------------------------------------------------
            # STRICT MAX JOB LIMIT
            # ------------------------------------------------

            if (
                len(keyword_jobs)
                >= max_jobs_per_keyword
            ):

                logger.info(
                    "Reached max_jobs_per_keyword=%s for '%s'",
                    max_jobs_per_keyword,
                    keyword
                )

                break

            # ------------------------------------------------
            # NO NEW JOBS
            # ------------------------------------------------

            if page_new == 0:

                logger.info(
                    "No new jobs found on page %s. Stopping pagination.",
                    page_number
                )

                break

            # ------------------------------------------------
            # DELAY BETWEEN PAGES
            # ------------------------------------------------

            if start + jobs_per_page < max_jobs_per_keyword:

                delay = random.uniform(
                    MIN_DELAY,
                    MAX_DELAY
                )

                logger.info(
                    "Waiting %.2f seconds before next page...",
                    delay
                )

                time.sleep(
                    delay
                )

        # ====================================================
        # KEYWORD SUMMARY
        # ====================================================

        logger.info(
            "Keyword '%s' collected %s jobs",
            keyword,
            len(keyword_jobs)
        )

    # ========================================================
    # DETAIL PAGE ENRICHMENT
    # ========================================================

    if enable_detail_pages and all_jobs:

        logger.info(
            "=" * 72
        )

        logger.info(
            "STARTING LINKEDIN DETAIL PAGE ENRICHMENT"
        )

        logger.info(
            "Jobs to enrich: %s",
            len(all_jobs)
        )

        logger.info(
            "=" * 72
        )

        for index, job in enumerate(
            all_jobs,
            start=1
        ):

            logger.info(
                "Detail enrichment %s/%s",
                index,
                len(all_jobs)
            )

            try:

                enrich_job(
                    job
                )

            except Exception as exc:

                logger.warning(
                    "Detail enrichment failed: %s",
                    exc
                )

            # ----------------------------------------------
            # DELAY BETWEEN DETAIL REQUESTS
            # ----------------------------------------------

            if index < len(all_jobs):

                delay = random.uniform(
                    MIN_DELAY,
                    MAX_DELAY
                )

                time.sleep(
                    delay
                )

    # ========================================================
    # EXISTING ML PREDICTOR
    # ========================================================

    if enable_ml and all_jobs:

        logger.info(
            "=" * 72
        )

        logger.info(
            "STARTING EXISTING ML ENRICHMENT"
        )

        logger.info(
            "=" * 72
        )

        for index, job in enumerate(
            all_jobs,
            start=1
        ):

            logger.info(
                "ML enrichment %s/%s",
                index,
                len(all_jobs)
            )

            try:

                apply_existing_ml_predictor(
                    job
                )

            except Exception as exc:

                logger.warning(
                    "ML enrichment failed: %s",
                    exc
                )

    # ========================================================
    # NORMALIZATION
    # ========================================================

    normalized_jobs = []

    for job in all_jobs:

        try:

            normalized_job = normalize_job(
                job
            )

            normalized_jobs.append(
                normalized_job
            )

        except Exception as exc:

            logger.warning(
                "Job normalization failed: %s",
                exc
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    logger.info(
        "=" * 72
    )

    logger.info(
        "LINKEDIN JOB COLLECTION COMPLETED"
    )

    logger.info(
        "Total jobs collected: %s",
        len(normalized_jobs)
    )

    logger.info(
        "=" * 72
    )

    return normalized_jobs

# ============================================================
# ALIAS
# ============================================================

scrape_linkedin_jobs = (
    collect_linkedin_jobs
)


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    jobs = collect_linkedin_jobs(

        search_keywords=[
            "data analyst"
        ],

        location="India",

        max_jobs_per_keyword=5,

        jobs_per_page=5,

        # ----------------------------------------------------
        # TEST WITH LAST 1 HOUR
        # Change to 4 for last 4 hours.
        # ----------------------------------------------------

        max_age_hours=4,

        enable_detail_pages=True,

        enable_ml=False

    )

    print("")

    print(
        "=" * 72
    )

    print(
        "TEST RESULT:",
        len(jobs),
        "jobs"
    )

    print(
        "=" * 72
    )

    for job in jobs:

        print(
            "\n"
            f"Title       : {job.get('job_title')}\n"
            f"Company     : {job.get('company_name')}\n"
            f"Location    : {job.get('location')}\n"
            f"Posted      : {job.get('posted_date')}\n"
            f"Education   : {job.get('education')}\n"
            f"Skills      : {job.get('skills')}\n"
            f"Description : "
            f"{str(job.get('job_description', ''))[:300]}\n"
            f"URL         : {job.get('job_url')}\n"
        )