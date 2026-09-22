import csv

from pipeline.schema import UnifiedJob
from pipeline.storage import JobStore


def make_job(job_id, source="LinkedIn"):
    return UnifiedJob(job_id=job_id, source=source, title=f"Job {job_id}", link=f"https://example.com/{job_id}")


def test_append_jobs_writes_header_once_and_all_rows(tmp_path):
    store = JobStore(tmp_path)
    written = store.append_jobs([make_job("linkedin_1"), make_job("naukri_1", source="Naukri")])
    assert written == 2

    with open(store.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert {row["job_id"] for row in rows} == {"linkedin_1", "naukri_1"}


def test_append_jobs_is_additive_across_calls(tmp_path):
    store = JobStore(tmp_path)
    store.append_jobs([make_job("linkedin_1")])
    store.append_jobs([make_job("linkedin_2")])

    with open(store.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2


def test_append_jobs_with_empty_list_returns_zero_and_creates_nothing(tmp_path):
    store = JobStore(tmp_path)
    written = store.append_jobs([])
    assert written == 0
    assert not store.csv_path.exists()


def test_load_seen_ids_reads_existing_csv_job_ids(tmp_path):
    store = JobStore(tmp_path)
    store.append_jobs([make_job("linkedin_1"), make_job("linkedin_2")])

    seen = store.load_seen_ids()
    assert seen == {"linkedin_1", "linkedin_2"}


def test_load_seen_ids_merges_json_state_and_csv(tmp_path):
    store = JobStore(tmp_path)
    store.append_jobs([make_job("linkedin_1")])
    store.save_seen_ids({"linkedin_1", "linkedin_999_expired"})

    seen = store.load_seen_ids()
    assert seen == {"linkedin_1", "linkedin_999_expired"}


def test_load_seen_ids_on_missing_files_returns_empty_set(tmp_path):
    store = JobStore(tmp_path / "does-not-exist-yet")
    assert store.load_seen_ids() == set()


def test_load_seen_ids_tolerates_corrupt_json(tmp_path):
    store = JobStore(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    store.seen_path.write_text("{not valid json", encoding="utf-8")
    # Should not raise; corrupt state degrades to an empty starting set.
    assert store.load_seen_ids() == set()


def test_save_and_reload_seen_ids_round_trip(tmp_path):
    store = JobStore(tmp_path)
    store.save_seen_ids({"a", "b", "c"})
    assert store.load_seen_ids() == {"a", "b", "c"}
