import json

from pipeline.data_quality import check_experience
from pipeline.enrichment import enrich_job
from pipeline.normalizer import (
    _extract_experience_range,
    _parse_experience_text,
)
from pipeline.schema import UnifiedJob
from scrapers.linkedin.scraper import extract_skills as extract_linkedin_skills
from scrapers.naukri.scraper import (
    extract_education,
    extract_skills,
    extract_specialization,
)


class FakeNaukriResponse:
    def __init__(self, data):
        payload = json.dumps(data)
        self.body = (
            "<script type='application/ld+json'>"
            f"{payload}"
            "</script>"
        ).encode("utf-8")

    def css(self, selector):
        return []


def test_experience_range_is_parsed():
    assert _parse_experience_text("Experience: 2 to 5 years") == ("2", "5")


def test_plus_experience_has_no_maximum():
    assert _parse_experience_text("5+ years of experience") == (
        "5",
        "Not Specified",
    )


def test_malformed_naukri_experience_uses_url_range():
    result = _extract_experience_range(
        {
            "experience": "510 years",
            "link": "https://www.naukri.com/job-listings-java-ai-engineer-5-to-10-years-123",
        },
        "Experience: 510 Years.",
    )

    assert result == ("5", "10")


def test_malformed_experience_without_evidence_is_missing():
    assert _parse_experience_text("Experience: 510 Years") is None


def test_skill_specific_experience_is_not_overall_experience():
    assert _parse_experience_text(
        "Preferred: 1 year of experience in SQL."
    ) is None


def test_linkedin_r_requires_language_context():
    assert "R" not in extract_linkedin_skills(
        "Role: Java Developer. Required skills include Java, SQL and Spring Boot."
    )
    assert "R" in extract_linkedin_skills(
        "Experience with R programming, Python and SQL."
    )


def test_naukri_jsonld_extracts_skills_and_education():
    response = FakeNaukriResponse(
        {
            "skills": ["SQL", "Python", "Power BI"],
            "qualifications": {
                "educationalLevel": (
                    "B.Tech / B.E. in Any Specialization, Any Graduate"
                )
            },
        }
    )

    assert extract_skills(response) == "SQL, Python, Power BI"
    assert "B.Tech" in extract_education(response)
    assert "B.E" in extract_education(response)
    assert "Any Graduate" in extract_education(response)
    assert extract_specialization(response) == "Any Specialization"


def test_naukri_preserves_graduation_not_required():
    response = FakeNaukriResponse(
        {
            "qualifications": {
                "educationalLevel": "Graduation Not Required"
            }
        }
    )

    assert extract_education(response) == "Graduation Not Required"


def test_source_education_is_not_overwritten_by_ml(monkeypatch):
    import pipeline.enrichment as enrichment

    monkeypatch.setattr(
        enrichment,
        "predict_job_details",
        lambda description: {
            "predicted_degree": "B.Tech",
            "predicted_specialization": "Civil Engineering",
        },
    )

    job = UnifiedJob(
        job_id="naukri_source_priority",
        source="Naukri",
        title="Data Analyst",
        company="Example",
        link="https://www.naukri.com/job-listings-example-123",
        degree_required="B.Tech",
        specialization_required="Any Specialization",
        full_description="SQL and Python",
    )

    enriched = enrich_job(job)

    assert enriched.degree_required == "B.Tech"
    assert enriched.specialization_required == "Any Specialization"


def test_data_quality_flags_experience_above_100():
    problems = check_experience(
        [
            {
                "min_experience_years": "510",
                "max_experience_years": "510",
            }
        ]
    )

    assert any(
        field == "min_experience_years"
        and "suspicious" in value
        for _, field, value in problems
    )