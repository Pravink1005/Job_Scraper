from datetime import datetime, timedelta

from scrapers.naukri.scraper import (
    build_page_url,
    build_search_urls_from_titles,
    clean_company_name,
    clean_education,
    clean_skills,
    compact_text,
    is_last_day_posting,
    parse_posted_date,
    slugify_title,
)


def test_slugify_title_basic():
    assert slugify_title("Data Analyst") == "data-analyst"


def test_slugify_title_strips_punctuation():
    assert slugify_title("Sr. ML Engineer") == "sr-ml-engineer"


def test_slugify_title_empty_returns_none():
    assert slugify_title("") is None
    assert slugify_title(None) is None


def test_build_search_urls_from_titles_list():
    urls = build_search_urls_from_titles(["data analyst", "data engineer"])
    assert urls == [
        "https://www.naukri.com/data-analyst-jobs?jobAge=1",
        "https://www.naukri.com/data-engineer-jobs?jobAge=1",
    ]


def test_build_search_urls_from_titles_comma_separated_string():
    urls = build_search_urls_from_titles("data analyst, business analyst")
    assert len(urls) == 2
    assert "business-analyst-jobs" in urls[1]


def test_build_search_urls_from_titles_skips_empty_entries():
    urls = build_search_urls_from_titles(["data analyst", "", "   "])
    assert len(urls) == 1


def test_build_page_url_page_one_is_unchanged():
    url = "https://www.naukri.com/data-analyst-jobs?jobAge=1"
    assert build_page_url(url, 1) == url


def test_build_page_url_appends_page_number_to_path_not_query():
    url = "https://www.naukri.com/data-analyst-jobs?jobAge=1"
    assert build_page_url(url, 2) == "https://www.naukri.com/data-analyst-jobs-2?jobAge=1"


def test_parse_posted_date_today():
    result = parse_posted_date("Posted today")
    expected_prefix = datetime.now().strftime("%d/%m/%Y")
    assert result.startswith(expected_prefix)


def test_parse_posted_date_n_days_ago():
    result = parse_posted_date("Posted 5 days ago")
    expected = (datetime.now() - timedelta(days=5)).strftime("%d/%m/%Y")
    assert result.startswith(expected)


def test_parse_posted_date_unparsable_returns_original_text():
    assert parse_posted_date("some odd phrase") == "some odd phrase"


def test_parse_posted_date_empty_returns_none():
    assert parse_posted_date("") is None
    assert parse_posted_date(None) is None


def test_is_last_day_posting_true_cases():
    assert is_last_day_posting("Posted today") is True
    assert is_last_day_posting("Posted just now") is True
    assert is_last_day_posting("Posted 1 day ago") is True
    assert is_last_day_posting("Posted 3 hours ago") is True


def test_is_last_day_posting_false_for_older_postings():
    assert is_last_day_posting("Posted 2 days ago") is False
    assert is_last_day_posting("Posted 11 days ago") is False
    assert is_last_day_posting("Posted 21 days ago") is False


def test_is_last_day_posting_regression_no_false_positive_on_11_21_31_days():
    """
    Regression test: a naive substring check for '1 day' would incorrectly
    match inside '11 days', '21 days', '31 days', etc. because the digit
    '1', a space, and 'day' all appear there too.
    """
    for text in ["Posted 11 days ago", "Posted 21 days ago", "Posted 31 days ago", "Posted 41 days ago"]:
        assert is_last_day_posting(text) is False


def test_is_last_day_posting_false_for_empty():
    assert is_last_day_posting("") is False
    assert is_last_day_posting(None) is False


def test_clean_company_name_removes_review_count():
    assert clean_company_name("Acme Corp\n4.2K Reviews") == "Acme Corp"


def test_clean_company_name_handles_none():
    assert clean_company_name(None) is None


def test_compact_text_collapses_whitespace():
    assert compact_text("  hello   \n world  ") == "hello world"


def test_compact_text_handles_none_and_empty():
    assert compact_text(None) is None
    assert compact_text("") is None


def test_clean_education_strips_labels():
    assert clean_education("Education UG: B.Tech PG: MBA") == "B.Tech; MBA"


def test_clean_education_handles_none():
    assert clean_education(None) is None


def test_clean_skills_dedupes_case_insensitively_preserving_order():
    result = clean_skills(["SQL", "Excel", "sql", "Power BI", "  ", "Excel"])
    assert result == "SQL; Excel; Power BI"


def test_clean_skills_empty_list_returns_not_specified():
    assert clean_skills([]) == "Not specified"
