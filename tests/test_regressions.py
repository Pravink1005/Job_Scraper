from pipeline.normalizer import normalize_linkedin_job, normalize_naukri_job
from ml.ml_predictor import detect_explicit_specialization
from scrapers.linkedin.scraper import NOT_SPECIFIED as LINKEDIN_NOT_SPECIFIED


def test_naukri_generic_title_recovers_from_slug():
    job = normalize_naukri_job({
        "title": "Job description",
        "company": "Acme",
        "location": "Bengaluru",
        "url": "https://www.naukri.com/job-listings-senior-python-developer-acme-bengaluru-0-to-1-years-123456",
    })
    assert job.title == "senior python developer"


def test_software_architecture_is_not_civil_but_civil_engineer_is():
    assert detect_explicit_specialization(
        "Python developer building microservice architecture"
    ) != "Civil Engineering"
    assert detect_explicit_specialization(
        "Civil engineer designing structural systems"
    ) == "Civil Engineering"


def test_naukri_html_is_stripped():
    job = normalize_naukri_job({
        "title": "Python Developer",
        "url": "https://www.naukri.com/job-listings-python-developer-acme-bengaluru-1-to-2-years-1",
        "full_description": "<p>Build &amp; test</p><li>APIs</li>",
    })
    assert job.full_description == "Build & test APIs"


def test_naukri_url_supplies_min_and_max_experience():
    job = normalize_naukri_job({
        "title": "Python Developer",
        "url": "https://www.naukri.com/job-listings-python-developer-acme-bengaluru-2-to-5-years-1",
        "full_description": "2 months experience",
    })
    assert job.min_experience_years == "2"
    assert job.max_experience_years == "5"


def test_bare_degree_is_removed():
    job = normalize_linkedin_job({
        "title": "Python Developer",
        "link": "https://www.linkedin.com/jobs/view/1",
        "degree_required": "degree",
    })
    assert job.degree_required == "Not Specified"


def test_placeholder_casing_is_unified():
    assert LINKEDIN_NOT_SPECIFIED == "Not Specified"


def test_naukri_url_wins_over_fractional_experience():
    job = normalize_naukri_job({
        "title": "Python Developer",
        "url": "https://www.naukri.com/job-listings-python-developer-acme-bengaluru-0-to-1-years-1",
        "full_description": "1 month experience",
    })
    assert job.min_experience_years == "0"
    assert job.max_experience_years == "1"
