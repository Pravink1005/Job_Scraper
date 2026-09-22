import pytest

from pipeline.errors import DataValidationError
from pipeline.normalizer import normalize, normalize_linkedin_job, normalize_naukri_job


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------

def _linkedin_raw(**overrides):
    base = {
        "job_id": "linkedin_4213567890",
        "category": "Python Backend Developer",
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "city": "Bengaluru",
        "state": "",
        "country": "India",
        "source": "LinkedIn",
        "collected_at": "2026-09-20T10:00:00",
        "posted_time": "20-09-2026 09:00",
        "link": "https://www.linkedin.com/jobs/view/4213567890/",
        "full_description": "We need Python, Django and PostgreSQL experience.",
        "skills": "Python; Django; PostgreSQL",
        "degree_required": "Bachelor's Degree",
        "specialization_required": "Software Engineering",
        "min_experience_years": "3",
        "max_experience_years": "5",
    }
    base.update(overrides)
    return base


def test_normalize_linkedin_happy_path():
    job = normalize_linkedin_job(_linkedin_raw())
    assert job.source == "LinkedIn"
    assert job.job_id == "linkedin_4213567890"
    assert job.company == "Acme Corp"
    assert job.city == "Bengaluru"
    assert job.skills == "Python; Django; PostgreSQL"
    assert job.degree_required == "Bachelor's Degree"


def test_normalize_linkedin_missing_link_raises():
    raw = _linkedin_raw(link="")
    with pytest.raises(DataValidationError) as exc_info:
        normalize_linkedin_job(raw)
    assert exc_info.value.field == "link"
    assert exc_info.value.source == "LinkedIn"


def test_normalize_linkedin_missing_title_raises():
    raw = _linkedin_raw(title=None)
    with pytest.raises(DataValidationError) as exc_info:
        normalize_linkedin_job(raw)
    assert exc_info.value.field == "title"


def test_normalize_linkedin_missing_job_id_falls_back_to_hash():
    raw = _linkedin_raw(job_id=None)
    job = normalize_linkedin_job(raw)
    assert job.job_id.startswith("linkedin_unknown_")


def test_normalize_linkedin_blank_optional_fields_get_placeholders():
    raw = _linkedin_raw(company="", city="", skills="", degree_required="")
    job = normalize_linkedin_job(raw)
    assert job.company == "N/A"
    assert job.city == "Not Specified"
    assert job.skills == "Not specified"
    assert job.degree_required == "Not Specified"


# ---------------------------------------------------------------------------
# Naukri
# ---------------------------------------------------------------------------

def _naukri_raw(**overrides):
    base = {
        "url": "https://www.naukri.com/job-listings-data-analyst-acme-bengaluru-1234",
        "title": "Data Analyst",
        "company": "Acme Corp",
        "location": "Bengaluru, Hyderabad, Pune",
        "experience": "2-5 Yrs",
        "salary": "Not disclosed",
        "skills": "SQL; Excel; Power BI",
        "qualifications_education_required": "Any Graduate",
        "job_description_summary": "Analyze data using SQL and Excel.",
        "posted": "20/09/2026 00:00:00",
    }
    base.update(overrides)
    return base


def test_normalize_naukri_happy_path():
    job = normalize_naukri_job(_naukri_raw())
    assert job.source == "Naukri"
    assert job.job_id.startswith("naukri_")
    assert job.city == "Bengaluru"
    assert job.country == "India"
    assert job.min_experience_years == "2"
    assert job.max_experience_years == "5"
    assert job.degree_required == "Any Graduate"
    assert job.specialization_required == "Not Specified"
    assert job.posted_time == "20-09-2026 00:00"


def test_normalize_naukri_missing_url_raises():
    raw = _naukri_raw(url="")
    with pytest.raises(DataValidationError) as exc_info:
        normalize_naukri_job(raw)
    assert exc_info.value.field == "url"
    assert exc_info.value.source == "Naukri"


def test_normalize_naukri_missing_title_raises():
    raw = _naukri_raw(title=None)
    with pytest.raises(DataValidationError):
        normalize_naukri_job(raw)


def test_normalize_naukri_single_experience_value():
    job = normalize_naukri_job(_naukri_raw(experience="3 Yrs"))
    assert job.min_experience_years == "3"
    assert job.max_experience_years == "3"


def test_normalize_naukri_unparsable_experience_falls_back_to_raw_text():
    job = normalize_naukri_job(_naukri_raw(experience="Freshers"))
    assert job.min_experience_years == "Freshers"
    assert job.max_experience_years == "Freshers"


def test_normalize_naukri_missing_experience_is_not_specified():
    job = normalize_naukri_job(_naukri_raw(experience=None))
    assert job.min_experience_years == "Not Specified"
    assert job.max_experience_years == "Not Specified"


def test_normalize_naukri_unparsable_posted_date_kept_as_is():
    job = normalize_naukri_job(_naukri_raw(posted="some odd text"))
    assert job.posted_time == "some odd text"


def test_normalize_naukri_missing_posted_date():
    job = normalize_naukri_job(_naukri_raw(posted=None))
    assert job.posted_time == "Not Specified"


def test_normalize_naukri_job_id_is_stable_for_same_url():
    job_a = normalize_naukri_job(_naukri_raw())
    job_b = normalize_naukri_job(_naukri_raw(title="Different Title"))
    assert job_a.job_id == job_b.job_id  # same url -> same id, regardless of other fields


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def test_normalize_dispatch_linkedin():
    job = normalize("linkedin", _linkedin_raw())
    assert job.source == "LinkedIn"


def test_normalize_dispatch_naukri_case_insensitive():
    job = normalize("Naukri", _naukri_raw())
    assert job.source == "Naukri"


def test_normalize_dispatch_unknown_source_raises():
    with pytest.raises(DataValidationError) as exc_info:
        normalize("indeed", {"title": "x", "url": "y"})
    assert exc_info.value.field == "source"
