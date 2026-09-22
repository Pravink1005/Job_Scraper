from datetime import datetime, timedelta

from scrapers.linkedin.scraper import (
    get_canonical_job_id,
    has_absolute_posted_time,
    is_recent_posted_time,
    normalize_linkedin_job_url,
    parse_relative_posted_time,
)


def test_normalize_linkedin_job_url_extracts_canonical_view_url():
    url = "https://www.linkedin.com/jobs/view/4213567890/?refId=abc&trackingId=xyz"
    assert normalize_linkedin_job_url(url) == "https://www.linkedin.com/jobs/view/4213567890/"


def test_normalize_linkedin_job_url_handles_missing_url():
    assert normalize_linkedin_job_url("") == "N/A"
    assert normalize_linkedin_job_url(None) == "N/A"


def test_normalize_linkedin_job_url_falls_back_for_non_matching_urls():
    url = "https://www.linkedin.com/jobs/collections/recommended/?query=abc"
    result = normalize_linkedin_job_url(url)
    assert result.endswith("/")
    assert "?" not in result


def test_get_canonical_job_id_uses_numeric_id():
    url = "https://www.linkedin.com/jobs/view/4213567890/"
    assert get_canonical_job_id(url) == "linkedin_4213567890"


def test_get_canonical_job_id_falls_back_to_hash_for_unusual_urls():
    job_id = get_canonical_job_id("https://www.linkedin.com/jobs/collections/recommended/")
    assert job_id.startswith("linkedin_unknown_")


def test_has_absolute_posted_time_true_for_dd_mm_yyyy_hh_mm():
    assert has_absolute_posted_time("20-09-2026 10:00") is True


def test_has_absolute_posted_time_false_for_relative_text():
    assert has_absolute_posted_time("2 hours ago") is False
    assert has_absolute_posted_time("Not Specified") is False
    assert has_absolute_posted_time(None) is False


def test_parse_relative_posted_time_minutes_and_hours():
    now = datetime.now()
    parsed_minutes = parse_relative_posted_time("30 minutes ago")
    parsed_hours = parse_relative_posted_time("2 hours ago")
    assert abs((now - parsed_minutes).total_seconds() - 30 * 60) < 5
    assert abs((now - parsed_hours).total_seconds() - 2 * 3600) < 5


def test_parse_relative_posted_time_today_and_yesterday():
    now = datetime.now()
    assert abs((parse_relative_posted_time("Today") - now).total_seconds()) < 5
    yesterday = parse_relative_posted_time("Yesterday")
    assert abs((now - yesterday) - timedelta(days=1)) < timedelta(seconds=5)


def test_parse_relative_posted_time_unparsable_returns_none():
    assert parse_relative_posted_time("") is None
    assert parse_relative_posted_time("Not Specified") is None
    assert parse_relative_posted_time("gibberish text with no time info") is None


def test_is_recent_posted_time_within_window():
    assert is_recent_posted_time("30 minutes ago", max_age_hours=1) is True


def test_is_recent_posted_time_outside_window():
    assert is_recent_posted_time("3 hours ago", max_age_hours=1) is False


def test_is_recent_posted_time_unparsable_is_not_recent():
    assert is_recent_posted_time("Not Specified", max_age_hours=1) is False
