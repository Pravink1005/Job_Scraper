import pytest

from pipeline.errors import PipelineError, ScraperError
from pipeline.orchestrator import run_pipeline
from pipeline.storage import JobStore


def _linkedin_raw(job_id="linkedin_1"):
    return {
        "job_id": job_id,
        "title": "Backend Engineer",
        "company": "Acme",
        "city": "Bengaluru",
        "link": f"https://www.linkedin.com/jobs/view/{job_id}/",
        "full_description": "Python, Django required.",
        "skills": "Python; Django",
        "degree_required": "Bachelor's Degree",
        "specialization_required": "Software Engineering",
        "min_experience_years": "2",
        "max_experience_years": "4",
        "search_keyword": "backend engineer",
        "collected_at": "2026-09-20T10:00:00",
    }


def _naukri_raw(url="https://www.naukri.com/job/1"):
    return {
        "url": url,
        "title": "Data Analyst",
        "company": "Acme",
        "location": "Bengaluru",
        "experience": "2-4 Yrs",
        "skills": "SQL; Excel",
        "qualifications_education_required": "Any Graduate",
        "job_description_summary": "Analyze data.",
        "search_keyword": "data analyst",
    }


def test_run_pipeline_with_both_sources_succeeding(tmp_path):
    store = JobStore(tmp_path)

    def fake_linkedin(**kwargs):
        return [_linkedin_raw("linkedin_1"), _linkedin_raw("linkedin_2")]

    def fake_naukri(**kwargs):
        return [_naukri_raw("https://www.naukri.com/job/1")]

    report = run_pipeline(
        store=store,
        linkedin_collector=fake_linkedin, linkedin_kwargs={},
        naukri_collector=fake_naukri, naukri_kwargs={},
        apply_enrichment=False,
    )

    assert report.new_jobs_written == 3
    assert not report.any_source_failed
    assert {r.source for r in report.results} == {"LinkedIn", "Naukri"}


def test_run_pipeline_isolates_one_source_failure(tmp_path):
    store = JobStore(tmp_path)

    def failing_linkedin(**kwargs):
        raise ScraperError("LinkedIn", "every search request failed")

    def fake_naukri(**kwargs):
        return [_naukri_raw()]

    report = run_pipeline(
        store=store,
        linkedin_collector=failing_linkedin, linkedin_kwargs={},
        naukri_collector=fake_naukri, naukri_kwargs={},
        apply_enrichment=False,
    )

    linkedin_result = next(r for r in report.results if r.source == "LinkedIn")
    naukri_result = next(r for r in report.results if r.source == "Naukri")

    assert not linkedin_result.succeeded
    assert "every search request failed" in linkedin_result.error
    assert naukri_result.succeeded
    assert report.new_jobs_written == 1  # Naukri's job still made it through


def test_run_pipeline_skips_invalid_records_without_failing_the_source(tmp_path):
    store = JobStore(tmp_path)

    def fake_linkedin(**kwargs):
        good = _linkedin_raw("linkedin_1")
        bad = _linkedin_raw("linkedin_2")
        bad["link"] = ""  # invalid: normalizer will reject this one
        return [good, bad]

    report = run_pipeline(
        store=store,
        linkedin_collector=fake_linkedin, linkedin_kwargs={},
        apply_enrichment=False,
    )

    result = report.results[0]
    assert result.succeeded
    assert result.collected == 2
    assert result.normalized == 1
    assert result.skipped_invalid == 1
    assert report.new_jobs_written == 1


def test_run_pipeline_deduplicates_against_previously_seen_ids(tmp_path):
    store = JobStore(tmp_path)
    store.save_seen_ids({"linkedin_1"})

    def fake_linkedin(**kwargs):
        return [_linkedin_raw("linkedin_1"), _linkedin_raw("linkedin_2")]

    report = run_pipeline(store=store, linkedin_collector=fake_linkedin, linkedin_kwargs={}, apply_enrichment=False)

    assert report.new_jobs_written == 1  # linkedin_1 already seen, only linkedin_2 is new


def test_run_pipeline_unexpected_exception_is_isolated_not_propagated(tmp_path):
    store = JobStore(tmp_path)

    def buggy_linkedin(**kwargs):
        raise ValueError("some unrelated bug")

    def fake_naukri(**kwargs):
        return [_naukri_raw()]

    report = run_pipeline(
        store=store,
        linkedin_collector=buggy_linkedin, linkedin_kwargs={},
        naukri_collector=fake_naukri, naukri_kwargs={},
        apply_enrichment=False,
    )

    linkedin_result = next(r for r in report.results if r.source == "LinkedIn")
    assert not linkedin_result.succeeded
    assert "unrelated bug" in linkedin_result.error
    assert report.new_jobs_written == 1


def test_run_pipeline_with_no_collectors_raises_pipeline_error(tmp_path):
    store = JobStore(tmp_path)
    with pytest.raises(PipelineError):
        run_pipeline(store=store)


def test_run_pipeline_with_empty_results_writes_nothing(tmp_path):
    store = JobStore(tmp_path)

    def empty_linkedin(**kwargs):
        return []

    report = run_pipeline(store=store, linkedin_collector=empty_linkedin, linkedin_kwargs={}, apply_enrichment=False)
    assert report.new_jobs_written == 0
    assert not store.csv_path.exists()