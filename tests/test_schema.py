from pipeline.schema import CSV_FIELDS, UnifiedJob


def test_unified_job_defaults():
    job = UnifiedJob(job_id="linkedin_123", source="LinkedIn", title="Backend Engineer", link="https://example.com/1")
    assert job.company == "N/A"
    assert job.city == "Not Specified"
    assert job.skills == "Not specified"
    assert job.degree_required == "Not Specified"


def test_to_csv_row_has_all_fields_in_order():
    job = UnifiedJob(job_id="naukri_abc", source="Naukri", title="Data Analyst", link="https://naukri.com/job/1")
    row = job.to_csv_row()
    assert list(row.keys()) == CSV_FIELDS
    assert row["job_id"] == "naukri_abc"
    assert row["source"] == "Naukri"


def test_to_csv_row_is_plain_strings_and_serializable():
    job = UnifiedJob(
        job_id="linkedin_999", source="LinkedIn", title="ML Engineer", link="https://example.com/2",
        min_experience_years="3", max_experience_years="5+",
    )
    row = job.to_csv_row()
    assert row["min_experience_years"] == "3"
    assert row["max_experience_years"] == "5+"
    # every value must be a plain (csv-writable) type
    assert all(isinstance(v, str) for v in row.values())
