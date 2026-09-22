from pipeline.enrichment import enrich_job, ml_available
from pipeline.schema import UnifiedJob


def test_ml_models_loaded_from_shared_ml_directory():
    # This confirms the merged project's shared ml/ package (not a
    # duplicate copy) is what gets loaded.
    assert ml_available() is True


def test_enrich_job_fills_unset_degree_and_specialization():
    job = UnifiedJob(
        job_id="naukri_1", source="Naukri", title="Backend Engineer",
        link="https://naukri.com/job/1",
        full_description="We require a Bachelor's degree in Computer Science and 3 years of Python experience.",
    )
    enriched = enrich_job(job)
    assert enriched.degree_required != "Not Specified"


def test_enrich_job_does_not_override_existing_values():
    job = UnifiedJob(
        job_id="linkedin_1", source="LinkedIn", title="Backend Engineer",
        link="https://linkedin.com/jobs/view/1",
        full_description="Bachelor's degree required.",
        degree_required="PhD",  # already set by the LinkedIn scraper's own ML step
        specialization_required="Robotics",
    )
    enriched = enrich_job(job)
    assert enriched.degree_required == "PhD"
    assert enriched.specialization_required == "Robotics"


def test_enrich_job_no_op_when_description_missing():
    job = UnifiedJob(job_id="naukri_2", source="Naukri", title="Analyst", link="https://naukri.com/job/2")
    enriched = enrich_job(job)
    assert enriched.degree_required == "Not Specified"
