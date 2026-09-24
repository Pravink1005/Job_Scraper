# ============================================================
# Naukri Job Scraper
# Production-compatible Scrapling version
# ============================================================

import logging
import json
import re
import time

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

try:
    from scrapling.fetchers import StealthyFetcher
except ImportError:
    StealthyFetcher = None


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.naukri.com"

DEFAULT_SEARCH_URLS = [
    "https://www.naukri.com/data-analyst-jobs?jobAge=1"
]

HEADLESS = True
WAIT_MS = 5000
REQUEST_TIMEOUT = 60000

MAX_RETRIES = 3
ENABLE_DETAIL_PAGES = False
DETAIL_DELAY_SECONDS = 0.5

NOT_SPECIFIED = "Not Specified"


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
# BASIC HELPERS
# ============================================================

def clean_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\xa0", " ")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_value(value: Any) -> str:

    text = clean_text(value)

    if not text:
        return NOT_SPECIFIED

    return text


def get_element_text(element: Any) -> str:

    if element is None:
        return ""

    try:
        text = element.text

        if text:
            return clean_text(text)

    except Exception:
        pass

    try:
        text = element.get_text()

        if text:
            return clean_text(text)

    except Exception:
        pass

    return ""


def get_attribute(
    element: Any,
    attribute: str
) -> str:

    if element is None:
        return ""

    try:
        value = element.attrib.get(
            attribute
        )

        if value:
            return clean_text(value)

    except Exception:
        pass

    try:
        value = element.get(
            attribute
        )

        if value:
            return clean_text(value)

    except Exception:
        pass

    return ""


def first_text(
    element: Any,
    selectors: List[str]
) -> str:

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            if found:

                text = get_element_text(
                    found[0]
                )

                if text:
                    return text

        except Exception:
            continue

    return ""


# ============================================================
# SCRAPLING FETCH
# ============================================================

def fetch_page(
    url: str,
    headless: bool = True,
    retries: int = MAX_RETRIES
):

    if StealthyFetcher is None:

        raise ImportError(
            "Scrapling is not installed. "
            "Install it with: pip install scrapling"
        )

    for attempt in range(
        1,
        retries + 1
    ):

        try:

            logger.info(
                "Fetching Naukri page: %s",
                url
            )

            # ------------------------------------------------
            # CURRENT SCRAPLING API
            #
            # Do NOT use:
            #
            # StealthyFetcher(...)
            # fetcher.get(...)
            #
            # Current API:
            #
            # StealthyFetcher.fetch(...)
            # ------------------------------------------------

            response = StealthyFetcher.fetch(
                url,
                headless=headless,
                network_idle=False,
                wait=WAIT_MS,
                timeout=REQUEST_TIMEOUT,
                google_search=True,
            )

            status_code = getattr(
                response,
                "status_code",
                None
            )

            # Some Scrapling versions expose
            # status instead of status_code.
            if status_code is None:

                status_code = getattr(
                    response,
                    "status",
                    None
                )

            logger.info(
                "Fetched page: HTTP %s",
                status_code
            )

            if (
                status_code == 200
                or status_code is None
            ):

                return response

            logger.warning(
                "Unexpected HTTP status: %s",
                status_code
            )

        except Exception as exc:

            logger.warning(
                "Fetch attempt %s/%s failed: %s",
                attempt,
                retries,
                exc
            )

        if attempt < retries:

            time.sleep(
                2 * attempt
            )

    return None


# ============================================================
# URL HELPERS
# ============================================================

def clean_url(url: str) -> str:

    if not url:
        return ""

    url = clean_text(url)

    if url.startswith("//"):

        url = "https:" + url

    elif url.startswith("/"):

        url = urljoin(
            BASE_URL,
            url
        )

    if not url.startswith("http"):
        return ""

    return url


def extract_job_id_from_url(
    url: str
) -> str:

    if not url:
        return ""

    url = clean_url(
        url
    )

    patterns = [

        r"-(\d+)\?src=",

        r"-(\d+)$",

        r"-(\d+)\?",

        r"jobid[=/](\d+)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    numbers = re.findall(
        r"\d{5,}",
        url
    )

    if numbers:
        return numbers[-1]

    return ""


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience_from_url(
    url: str
) -> str:

    if not url:
        return NOT_SPECIFIED

    patterns = [

        r"(\d+)-to-(\d+)-years",

        r"(\d+)-to-(\d+)-year",

        r"(\d+)-(\d+)-years",

        r"(\d+)-(\d+)-year",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url,
            re.IGNORECASE
        )

        if match:

            minimum = match.group(1)
            maximum = match.group(2)

            return (
                f"{minimum} to "
                f"{maximum} years"
            )

    return NOT_SPECIFIED


def extract_experience_from_text(
    text: str
) -> str:

    text = clean_text(
        text
    )

    if not text:
        return NOT_SPECIFIED

    patterns = [

        r"(\d+)\s*(?:to|-)\s*(\d+)\s*years?",

        r"(\d+)\s*(?:to|-)\s*(\d+)\s*yrs?",

        r"(\d+)\s*\+\s*years?",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        groups = match.groups()

        if len(groups) == 2:

            return (
                f"{groups[0]} to "
                f"{groups[1]} years"
            )

        if len(groups) == 1:

            return (
                f"{groups[0]}+ years"
            )

    return NOT_SPECIFIED


# ============================================================
# SALARY
# ============================================================

def extract_salary(
    element: Any
) -> str:

    selectors = [

        "[class*='salary']",

        "[class*='Salary']",

        "[class*='compensation']",

    ]

    text = first_text(
        element,
        selectors
    )

    if text:
        return text

    return NOT_SPECIFIED


# ============================================================
# POSTED DATE
# ============================================================

def parse_posted_date_text(
    text: str
) -> str:

    text = clean_text(
        text
    )

    if not text:
        return NOT_SPECIFIED

    now = datetime.now()

    match = re.search(
        r"(\d+)\s*minutes?\s*ago",
        text,
        re.IGNORECASE
    )

    if match:

        minutes = int(
            match.group(1)
        )

        value = (
            now -
            timedelta(
                minutes=minutes
            )
        )

        return value.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    match = re.search(
        r"(\d+)\s*hours?\s*ago",
        text,
        re.IGNORECASE
    )

    if match:

        hours = int(
            match.group(1)
        )

        value = (
            now -
            timedelta(
                hours=hours
            )
        )

        return value.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    match = re.search(
        r"(\d+)\s*days?\s*ago",
        text,
        re.IGNORECASE
    )

    if match:

        days = int(
            match.group(1)
        )

        value = (
            now -
            timedelta(
                days=days
            )
        )

        return value.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    if re.search(
        r"\byesterday\b",
        text,
        re.IGNORECASE
    ):

        value = (
            now -
            timedelta(days=1)
        )

        return value.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    date_patterns = [

        r"\d{1,2}/\d{1,2}/\d{4}",

        r"\d{1,2}-\d{1,2}-\d{4}",

        r"\d{1,2}\s+"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"(?:\s+\d{4})?",

    ]

    for pattern in date_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        value = match.group(0)

        formats = [

            "%d/%m/%Y",

            "%d-%m-%Y",

            "%d %b %Y",

            "%d %b",

        ]

        for fmt in formats:

            try:

                parsed = datetime.strptime(
                    value,
                    fmt
                )

                if fmt == "%d %b":

                    parsed = parsed.replace(
                        year=now.year
                    )

                return parsed.strftime(
                    "%d/%m/%Y %H:%M:%S"
                )

            except ValueError:
                continue

    return NOT_SPECIFIED


def extract_posted_date(
    element: Any
) -> str:

    selectors = [

        "[class*='date']",

        "[class*='Date']",

        "[class*='posted']",

        "[class*='Posted']",

    ]

    text = first_text(
        element,
        selectors
    )

    if text:

        parsed = (
            parse_posted_date_text(
                text
            )
        )

        if parsed != NOT_SPECIFIED:
            return parsed

    return NOT_SPECIFIED


# ============================================================
# COMPANY
# ============================================================

def clean_company(
    company: str
) -> str:

    company = clean_text(
        company
    )

    if not company:
        return NOT_SPECIFIED

    company = re.sub(
        r"\s*-\s*Openings?\s*$",
        "",
        company,
        flags=re.IGNORECASE
    )

    company = re.sub(
        r"\s*\|\s*Naukri.*$",
        "",
        company,
        flags=re.IGNORECASE
    )

    return company.strip()


def extract_company(
    element: Any
) -> str:

    selectors = [

        "a.comp-name",

        "a[class*='comp-name']",

        "span[class*='comp-name']",

        "div[class*='comp-name']",

        "[class*='companyName']",

        "[class*='company-name']",

        "[class*='CompanyName']",

    ]

    company = first_text(
        element,
        selectors
    )

    if company:
        return clean_company(
            company
        )

    return NOT_SPECIFIED


# ============================================================
# TITLE
# ============================================================

def extract_title(
    element: Any
) -> str:

    selectors = [

        "a.title",

        "a[class*='title']",

        "[class*='jobTitle']",

        "[class*='job-title']",

        "h2",

        "h3",

    ]

    title = first_text(
        element,
        selectors
    )

    if title:
        return title

    return NOT_SPECIFIED


# ============================================================
# LOCATION
# ============================================================

def clean_location(
    location: str
) -> str:

    location = clean_text(
        location
    )

    if not location:
        return NOT_SPECIFIED

    location = re.sub(
        r"^\s*location\s*[:\-]\s*",
        "",
        location,
        flags=re.IGNORECASE
    )

    return location.strip()


def extract_location(
    element: Any
) -> str:

    selectors = [

        "[class*='loc']",

        "[class*='Loc']",

        "[class*='location']",

        "[class*='Location']",

    ]

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            for item in found:

                text = get_element_text(
                    item
                )

                if not text:
                    continue

                text = clean_location(
                    text
                )

                if text == NOT_SPECIFIED:
                    continue

                if re.search(
                    r"\byears?\b",
                    text,
                    re.IGNORECASE
                ):
                    continue

                if re.search(
                    r"\bago\b",
                    text,
                    re.IGNORECASE
                ):
                    continue

                if len(text) > 150:
                    continue

                return text

        except Exception:
            continue

    return NOT_SPECIFIED


# ============================================================
# SKILLS
# ============================================================

def clean_skill(
    skill: str
) -> str:

    skill = clean_text(
        skill
    )

    skill = re.sub(
        r"^[•,\-|]+",
        "",
        skill
    )

    skill = re.sub(
        r"[,\-|]+$",
        "",
        skill
    )

    return skill.strip()


def _jsonld_records(
    element: Any
) -> List[Dict[str, Any]]:

    body = getattr(
        element,
        "body",
        b"",
    )

    if isinstance(body, bytes):
        body = body.decode(
            "utf-8",
            errors="ignore",
        )

    if not body:
        return []

    records = []

    script_pattern = (
        r"<script[^>]+type=[\"']application/ld\+json"
        r"[\"'][^>]*>(.*?)</script>"
    )

    for script in re.findall(
        script_pattern,
        body,
        flags=re.IGNORECASE | re.DOTALL,
    ):

        try:
            data = json.loads(script.strip())
        except (TypeError, json.JSONDecodeError):
            continue

        if isinstance(data, dict):
            records.append(data)

            graph = data.get("@graph")

            if isinstance(graph, list):
                records.extend(
                    item
                    for item in graph
                    if isinstance(item, dict)
                )

        elif isinstance(data, list):
            records.extend(
                item
                for item in data
                if isinstance(item, dict)
            )

    return records


def _extract_jsonld_skills(
    element: Any
) -> str:

    skills = []

    for record in _jsonld_records(element):

        value = record.get("skills")

        if isinstance(value, list):
            values = value
        else:
            values = [value]

        for skill in values:

            skill = clean_skill(
                str(skill or "")
            )

            if skill and skill not in skills:
                skills.append(skill)

    if not skills:
        return NOT_SPECIFIED

    return ", ".join(
        skills[:30]
    )


def _extract_jsonld_education(
    element: Any
) -> str:

    for record in _jsonld_records(element):

        qualifications = record.get(
            "qualifications"
        )

        if isinstance(qualifications, dict):
            qualifications = qualifications.get(
                "educationalLevel"
            )

        if qualifications:
            education = extract_education_from_text(
                str(qualifications)
            )

            if education != NOT_SPECIFIED:
                return education

    return NOT_SPECIFIED


def _extract_jsonld_specialization(
    element: Any
) -> str:

    specializations = []

    for record in _jsonld_records(element):

        qualifications = record.get(
            "qualifications"
        )

        if isinstance(qualifications, dict):
            qualifications = qualifications.get(
                "educationalLevel"
            )

        if not qualifications:
            continue

        matches = re.findall(
            r"\bin\s+([^,]+)",
            str(qualifications),
            flags=re.IGNORECASE,
        )

        for value in matches:

            value = clean_text(
                value
            )

            if value and value not in specializations:
                specializations.append(value)

    if not specializations:
        return NOT_SPECIFIED

    return ", ".join(
        specializations[:30]
    )


def _extract_jsonld_description(
    element: Any
) -> str:

    for record in _jsonld_records(element):

        description = record.get(
            "description"
        )

        if description:
            return clean_description(
                description
            )

    return NOT_SPECIFIED


def _extract_jsonld_experience(
    element: Any
) -> str:

    for record in _jsonld_records(element):

        requirements = record.get(
            "experienceRequirements"
        )

        if isinstance(requirements, dict):
            months = requirements.get(
                "monthsOfExperience"
            )

            if months is not None:
                try:
                    years = float(months) / 12
                except (TypeError, ValueError):
                    continue

                if years <= 100:
                    value = (
                        str(int(years))
                        if years.is_integer()
                        else str(round(years, 2))
                    )

                    return f"{value}+ years"

    return NOT_SPECIFIED


def extract_skills_from_text(
    text: str
) -> str:

    text = clean_text(
        text
    )

    if not text:
        return NOT_SPECIFIED

    match = re.search(
        r"\bkey\s+skills?\b\s*(.*?)(?=\b(?:education|additional information|role|industry type|department)\b|$)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return NOT_SPECIFIED

    skills_text = match.group(1).strip(" :|- ")
    skills = []

    known_skills = [
        "Cloud Computing",
        "Machine Learning",
        "Power BI",
        "DevOps",
        "Docker",
        "Kubernetes",
        "Terraform",
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "SQL",
        "AWS",
        "Azure",
        "GCP",
        "ECS",
        "CI/CD",
        "Git",
    ]

    for known_skill in known_skills:

        if re.search(
            rf"(?<![A-Za-z]){re.escape(known_skill)}(?![A-Za-z])",
            skills_text,
            flags=re.IGNORECASE,
        ):
            skills.append(known_skill)

    if skills:
        return ", ".join(skills[:30])

    for value in re.split(
        r"\s{2,}|\s*,\s*|\s*\|\s*",
        skills_text,
    ):

        value = clean_skill(value)

        if (
            value
            and value.lower() not in {"skills", "key skills"}
            and len(value) <= 60
            and value not in skills
        ):
            skills.append(value)

    if not skills:
        return NOT_SPECIFIED

    return ", ".join(
        skills[:30]
    )


def extract_skills(
    element: Any
) -> str:

    jsonld_skills = _extract_jsonld_skills(
        element
    )

    if jsonld_skills != NOT_SPECIFIED:
        return jsonld_skills

    selectors = [

        "[class*='skill']",

        "[class*='Skill']",

        "[class*='tags']",

        "[class*='Tags']",

    ]

    skills = []

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            for item in found:

                text = clean_skill(
                    get_element_text(item)
                )

                if not text:
                    continue

                if len(text) > 60:
                    continue

                if text.lower() in {
                    "skills",
                    "skill",
                    "key skills",
                }:
                    continue

                if text not in skills:

                    skills.append(
                        text
                    )

        except Exception:
            continue

    if not skills:
        return extract_skills_from_text(
            get_element_text(element)
        )

    return ", ".join(
        skills[:30]
    )


# ============================================================
# EDUCATION
# ============================================================

EDUCATION_PATTERNS = [

    r"\bB\.?\s*E\.?\b",

    r"\bB\.?\s*Tech\.?\b",

    r"\bB\.?\s*Sc\.?\b",

    r"\bB\.?\s*Com\.?\b",

    r"\bB\.?\s*C\.?\s*A\.?\b",

    r"\bB\.?\s*BA\b",

    r"\bM\.?\s*E\.?\b",

    r"\bM\.?\s*Tech\.?\b",

    r"\bM\.?\s*Sc\.?\b",

    r"\bM\.?\s*Com\.?\b",

    r"\bM\.?\s*CA\b",

    r"\bMBA\b",

    r"\bPh\.?\s*D\b",

    r"\bDiploma\b",

    r"\bBachelor(?:'s)?\b",

    r"\bMaster(?:'s)?\b",

    r"\bAny Graduate\b",

    r"\bAny Postgraduate\b",

    r"\bGraduation\s+Not\s+Required\b",

]


def extract_education_from_text(
    text: str
) -> str:

    text = clean_text(
        text
    )

    if not text:
        return NOT_SPECIFIED

    found = []

    for pattern in EDUCATION_PATTERNS:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            value = clean_text(
                match
            )

            if (
                value
                and value not in found
            ):

                found.append(
                    value
                )

    if not found:
        return NOT_SPECIFIED

    return ", ".join(
        found
    )


def extract_education(
    element: Any
) -> str:

    jsonld_education = _extract_jsonld_education(
        element
    )

    if jsonld_education != NOT_SPECIFIED:
        return jsonld_education

    selectors = [

        "[class*='education']",

        "[class*='Education']",

        "[class*='qualification']",

        "[class*='Qualification']",

        "[class*='degree']",

        "[class*='Degree']",

        "[class*='ug']",

        "[class*='pg']",

    ]

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            for item in found:

                text = get_element_text(
                    item
                )

                education = (
                    extract_education_from_text(
                        text
                    )
                )

                if (
                    education
                    != NOT_SPECIFIED
                ):

                    return education

        except Exception:
            continue

    try:

        full_text = get_element_text(
            element
        )

        education = (
            extract_education_from_text(
                full_text
            )
        )

        if education != NOT_SPECIFIED:
            return education

    except Exception:
        pass

    return NOT_SPECIFIED


def extract_education_from_card(
    element: Any
) -> str:

    return extract_education(
        element
    )


# ============================================================
# SPECIALIZATION
# ============================================================

def extract_specialization(
    element: Any
) -> str:

    jsonld_specialization = _extract_jsonld_specialization(
        element
    )

    if jsonld_specialization != NOT_SPECIFIED:
        return jsonld_specialization

    selectors = [

        "[class*='special']",

        "[class*='Special']",

        "[class*='stream']",

        "[class*='Stream']",

        "[class*='specialization']",

        "[class*='Specialization']",

    ]

    value = first_text(
        element,
        selectors
    )

    if value:
        return value

    return NOT_SPECIFIED


# ============================================================
# DESCRIPTION
# ============================================================

def clean_description(
    description: str
) -> str:

    description = clean_text(
        description
    )

    if not description:
        return NOT_SPECIFIED

    return description


def extract_description(
    element: Any
) -> str:

    jsonld_description = _extract_jsonld_description(
        element
    )

    if jsonld_description != NOT_SPECIFIED:
        return jsonld_description

    selectors = [

        "[class*='job-desc']",

        "[class*='jobDesc']",

        "[class*='description']",

        "[class*='Description']",

        "[class*='desc']",

        "[class*='Desc']",

    ]

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            for item in found:

                text = clean_description(
                    get_element_text(item)
                )

                if (
                    text != NOT_SPECIFIED
                    and len(text) > 30
                ):

                    return text

        except Exception:
            continue

    return NOT_SPECIFIED


# ============================================================
# CARD URL
# ============================================================

def extract_card_url(
    element: Any
) -> str:

    selectors = [

        "a.title",

        "a[class*='title']",

        "a[href*='job-listings']",

        "a[href*='job-listing']",

        "a[href*='naukri.com']",

    ]

    for selector in selectors:

        try:

            found = element.css(
                selector
            )

            for anchor in found:

                href = get_attribute(
                    anchor,
                    "href"
                )

                href = clean_url(
                    href
                )

                if href:
                    return href

        except Exception:
            continue

    try:

        anchors = element.css(
            "a"
        )

        for anchor in anchors:

            href = get_attribute(
                anchor,
                "href"
            )

            href = clean_url(
                href
            )

            if (
                href
                and "job-list" in href.lower()
            ):

                return href

    except Exception:
        pass

    return ""


# ============================================================
# SINGLE CARD
# ============================================================

def extract_job_from_card(
    card: Any
) -> Optional[Dict[str, Any]]:

    try:

        url = extract_card_url(
            card
        )

        if not url:
            return None

        job_id = extract_job_id_from_url(
            url
        )

        if not job_id:

            job_id = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                url
            )[-100:]

        title = extract_title(
            card
        )

        company = extract_company(
            card
        )

        location = extract_location(
            card
        )

        experience = (
            extract_experience_from_url(
                url
            )
        )

        if experience == NOT_SPECIFIED:

            experience = (
                extract_experience_from_text(
                    get_element_text(card)
                )
            )

        salary = extract_salary(
            card
        )

        skills = extract_skills(
            card
        )

        education = extract_education(
            card
        )

        specialization = (
            extract_specialization(
                card
            )
        )

        description = extract_description(
            card
        )

        posted_date = extract_posted_date(
            card
        )

        return {

            "job_id": f"naukri_{job_id}",

            "id": f"naukri_{job_id}",

            "source": "Naukri",

            "title": normalize_value(
                title
            ),

            "job_title": normalize_value(
                title
            ),

            "company": normalize_value(
                company
            ),

            "company_name": normalize_value(
                company
            ),

            "location": normalize_value(
                location
            ),

            "locations": normalize_value(
                location
            ),

            "experience": normalize_value(
                experience
            ),

            "salary": normalize_value(
                salary
            ),

            "skills": normalize_value(
                skills
            ),

            "education": normalize_value(
                education
            ),

            "degree_required": normalize_value(
                education
            ),

            "specialization": normalize_value(
                specialization
            ),

            "specialization_required": normalize_value(
                specialization
            ),

            "posted_date": normalize_value(
                posted_date
            ),

            "posted_time": normalize_value(
                posted_date
            ),

            "description": normalize_value(
                description
            ),

            "job_description": normalize_value(
                description
            ),

            "full_description": normalize_value(
                description
            ),

            "link": url,

            "url": url,

        }

    except Exception as exc:

        logger.warning(
            "Failed extracting Naukri card: %s",
            exc
        )

        return None


# ============================================================
# SEARCH CARDS
# ============================================================

def extract_search_cards(
    response: Any
) -> List[Any]:

    selectors = [

        "div.cust-job-tuple",

        "div[class*='cust-job-tuple']",

        "article[class*='jobTuple']",

        "div[class*='jobTuple']",

    ]

    for selector in selectors:

        try:

            cards = response.css(
                selector
            )

            if cards:

                logger.info(
                    "Found %s job cards using selector: %s",
                    len(cards),
                    selector
                )

                return list(cards)

        except Exception:
            continue

    logger.warning(
        "Naukri job-card markup NOT detected."
    )

    return []


# ============================================================
# DETAIL ENRICHMENT
# ============================================================

def enrich_job_from_detail(
    job: Dict[str, Any],
    response: Any
) -> Dict[str, Any]:

    if response is None:
        return job

    try:

        title = extract_title(
            response
        )

        if title != NOT_SPECIFIED:

            job["title"] = title
            job["job_title"] = title

        company = extract_company(
            response
        )

        if company != NOT_SPECIFIED:

            job["company"] = company
            job["company_name"] = company

        location = extract_location(
            response
        )

        if location != NOT_SPECIFIED:

            job["location"] = location
            job["locations"] = location

        experience = (
            extract_experience_from_text(
                get_element_text(response)
            )
        )

        if experience == NOT_SPECIFIED:
            experience = _extract_jsonld_experience(
                response
            )

        if experience != NOT_SPECIFIED:
            job["experience"] = experience

        salary = extract_salary(
            response
        )

        if salary != NOT_SPECIFIED:
            job["salary"] = salary

        education = extract_education(
            response
        )

        skills = extract_skills(
            response
        )

        if skills != NOT_SPECIFIED:
            job["skills"] = skills

        if education != NOT_SPECIFIED:

            job["education"] = education

            job["degree_required"] = (
                education
            )

        specialization = (
            extract_specialization(
                response
            )
        )

        if specialization != NOT_SPECIFIED:

            job["specialization"] = (
                specialization
            )

            job["specialization_required"] = (
                specialization
            )

        description = extract_description(
            response
        )

        if description != NOT_SPECIFIED:

            job["description"] = (
                description
            )

            job["job_description"] = (
                description
            )

            job["full_description"] = (
                description
            )

        posted_date = extract_posted_date(
            response
        )

        if posted_date != NOT_SPECIFIED:

            job["posted_date"] = (
                posted_date
            )

            job["posted_time"] = (
                posted_date
            )

    except Exception as exc:

        logger.warning(
            "Detail enrichment failed: %s",
            exc
        )

    return job


# ============================================================
# SEARCH PAGE
# ============================================================

def collect_from_search_page(
    url: str,
    headless: bool = True,
    max_total: int = 20
) -> List[Dict[str, Any]]:

    response = fetch_page(
        url,
        headless=headless
    )

    if response is None:
        return []

    cards = extract_search_cards(
        response
    )

    logger.info(
        "Search cards available: %s",
        len(cards)
    )

    jobs = []

    seen = set()

    for card in cards:

        if len(jobs) >= max_total:
            break

        job = extract_job_from_card(
            card
        )

        if not job:
            continue

        job_id = job.get(
            "job_id"
        )

        if not job_id:
            continue

        if job_id in seen:
            continue

        seen.add(
            job_id
        )

        jobs.append(
            job
        )

    logger.info(
        "Extracted %s unique Naukri jobs from search page.",
        len(jobs)
    )

    return jobs


# ============================================================
# NORMALIZE
# ============================================================

def normalize_job(
    job: Dict[str, Any]
) -> Dict[str, Any]:

    normalized = dict(
        job
    )

    fields = [

        "job_id",
        "source",
        "title",
        "company",
        "location",
        "experience",
        "salary",
        "skills",
        "education",
        "specialization",
        "posted_date",
        "description",
        "link",

    ]

    for field in fields:

        value = normalized.get(
            field
        )

        if value is None:

            normalized[field] = (
                NOT_SPECIFIED
            )

        else:

            normalized[field] = (
                clean_text(value)
                or NOT_SPECIFIED
            )

    if not normalized.get(
        "source"
    ):

        normalized["source"] = (
            "Naukri"
        )

    return normalized


# ============================================================
# PAGE URL
# ============================================================

def build_page_url(
    url: str,
    page_number: int
) -> str:

    if page_number <= 1:
        return url

    separator = (
        "&"
        if "?" in url
        else "?"
    )

    return (
        f"{url}"
        f"{separator}"
        f"page={page_number}"
    )


# ============================================================
# MAIN COLLECTOR
# ============================================================

def collect_naukri_jobs(
    search_urls: Optional[List[str]] = None,
    titles: Optional[List[str]] = None,
    max_pages: int = 5,
    max_total: int = 20,
    max_jobs: Optional[int] = None,
    headless: bool = True,
    enable_detail_pages: bool = ENABLE_DETAIL_PAGES,
) -> List[Dict[str, Any]]:

    # --------------------------------------------------------
    # Compatibility with main.py
    # --------------------------------------------------------

    if max_jobs is not None:
        max_total = max_jobs

    if max_total <= 0:
        return []

    if max_pages <= 0:
        max_pages = 1

    logger.info(
        "Starting Naukri search extraction"
    )

    logger.info(
        "Max pages: %s",
        max_pages
    )

    logger.info(
        "Max jobs: %s",
        max_total
    )

    logger.info(
        "Detail enrichment: %s",
        enable_detail_pages
    )

    # --------------------------------------------------------
    # Build search URLs
    # --------------------------------------------------------

    urls = []

    # Maps each search URL back to the keyword that produced it,
    # so every job collected from that URL can be tagged with
    # the keyword the user actually searched for.
    url_keywords: Dict[str, str] = {}

    if search_urls:

        for url in search_urls:

            if url:

                cleaned = clean_url(
                    url
                )

                if cleaned:
                    urls.append(
                        cleaned
                    )

    if titles:

        for title in titles:

            title = clean_text(
                title
            )

            if not title:
                continue

            slug = re.sub(
                r"[^a-zA-Z0-9]+",
                "-",
                title.lower()
            ).strip("-")

            if not slug:
                continue

            url = (
                f"{BASE_URL}/"
                f"{slug}-jobs?jobAge=1"
            )

            if url not in urls:

                urls.append(
                    url
                )

            # Tag this URL with its keyword, whether it was
            # just added above or already present from
            # search_urls.
            url_keywords[url] = title

    if not urls:

        urls = list(
            DEFAULT_SEARCH_URLS
        )

    # --------------------------------------------------------
    # Collect jobs
    # --------------------------------------------------------

    all_jobs = []

    seen_ids = set()

    for search_url in urls:

        if len(all_jobs) >= max_total:
            break

        logger.info(
            "Processing search URL: %s",
            search_url
        )

        for page_number in range(
            1,
            max_pages + 1
        ):

            if len(all_jobs) >= max_total:
                break

            page_url = build_page_url(
                search_url,
                page_number
            )

            logger.info(
                "Processing page %s: %s",
                page_number,
                page_url
            )

            remaining = (
                max_total -
                len(all_jobs)
            )

            jobs = collect_from_search_page(
                page_url,
                headless=headless,
                max_total=remaining
            )

            if not jobs:

                logger.info(
                    "No jobs found on page %s.",
                    page_number
                )

                continue

            new_jobs_on_page = 0

            for job in jobs:

                if len(all_jobs) >= max_total:
                    break

                job_id = job.get(
                    "job_id"
                )

                if not job_id:
                    continue

                if job_id in seen_ids:
                    continue

                seen_ids.add(
                    job_id
                )

                job["search_keyword"] = (
                    url_keywords.get(
                        search_url,
                        NOT_SPECIFIED,
                    )
                )

                # ------------------------------------------------
                # Optional detail page
                # ------------------------------------------------

                if enable_detail_pages:

                    link = job.get(
                        "link"
                    )

                    if (
                        link
                        and link != NOT_SPECIFIED
                    ):

                        detail_response = (
                            fetch_page(
                                link,
                                headless=headless
                            )
                        )

                        if detail_response:

                            job = (
                                enrich_job_from_detail(
                                    job,
                                    detail_response
                                )
                            )

                        time.sleep(
                            DETAIL_DELAY_SECONDS
                        )

                job = normalize_job(
                    job
                )

                all_jobs.append(
                    job
                )

                new_jobs_on_page += 1

            logger.info(
                "Page %s added %s new jobs.",
                page_number,
                new_jobs_on_page
            )

            if new_jobs_on_page == 0:
                break

    # --------------------------------------------------------
    # Final deduplication
    # --------------------------------------------------------

    final_jobs = []

    final_seen = set()

    for job in all_jobs:

        job = normalize_job(
            job
        )

        job_id = job.get(
            "job_id"
        )

        if not job_id:
            continue

        if job_id in final_seen:
            continue

        final_seen.add(
            job_id
        )

        final_jobs.append(
            job
        )

        if len(final_jobs) >= max_total:
            break

    logger.info(
        "Final unique jobs: %s",
        len(final_jobs)
    )

    return final_jobs


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

scrape_naukri_jobs = (
    collect_naukri_jobs
)

get_naukri_jobs = (
    collect_naukri_jobs
)


# ============================================================
# SUMMARY
# ============================================================

def print_job_summary(
    jobs: List[Dict[str, Any]]
):

    print()
    print("=" * 80)
    print("NAUKRI JOB SUMMARY")
    print("=" * 80)

    print(
        f"Total jobs: {len(jobs)}"
    )

    print()

    for index, job in enumerate(
        jobs,
        start=1
    ):

        print(
            f"{index}. "
            f"{job.get('title', NOT_SPECIFIED)}"
        )

        print(
            f"   Company    : "
            f"{job.get('company', NOT_SPECIFIED)}"
        )

        print(
            f"   Location   : "
            f"{job.get('location', NOT_SPECIFIED)}"
        )

        print(
            f"   Experience : "
            f"{job.get('experience', NOT_SPECIFIED)}"
        )

        print(
            f"   Salary     : "
            f"{job.get('salary', NOT_SPECIFIED)}"
        )

        print(
            f"   Education  : "
            f"{job.get('education', NOT_SPECIFIED)}"
        )

        print(
            f"   Skills     : "
            f"{job.get('skills', NOT_SPECIFIED)}"
        )

        print(
            f"   Posted     : "
            f"{job.get('posted_date', NOT_SPECIFIED)}"
        )

        print(
            f"   Link       : "
            f"{job.get('link', NOT_SPECIFIED)}"
        )

        description = job.get(
            "description",
            NOT_SPECIFIED
        )

        print(
            f"   Description: "
            f"{description[:200]}"
        )

        print("-" * 80)


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 80)
    print("NAUKRI SCRAPER DIRECT TEST")
    print("=" * 80)

    jobs = collect_naukri_jobs(

        search_urls=DEFAULT_SEARCH_URLS,

        titles=[
            "data analyst"
        ],

        max_pages=1,

        max_total=20,

        max_jobs=20,

        headless=True,

        enable_detail_pages=False,
    )

    print_job_summary(
        jobs
    )