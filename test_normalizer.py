from pipeline.normalizer import normalize_linkedin_job


def test_case(name, raw):
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    job = normalize_linkedin_job(raw)

    print("Company :", job.company)
    print("City    :", job.city)
    print("State   :", job.state)
    print("Country :", job.country)
    print("Degree  :", job.degree_required)


# ============================================================
# TEST 1 — COMPANY PREFIX
# ============================================================

test_case(
    "TEST 1 - Company prefix",
    {
        "job_id": "test_1",
        "job_title": "Data Analyst",
        "company_name": "Crunchyroll",
        "location": "Crunchyroll Hyderabad",
        "job_url": "https://example.com/1",
        "education": r"B\.?E\., Bachelor(?:'s)?, degree",
    },
)


# ============================================================
# TEST 2 — STATE + INDIA CONTAMINATION
# ============================================================

test_case(
    "TEST 2 - StateIndia contamination",
    {
        "job_id": "test_2",
        "job_title": "Data Analyst",
        "company_name": "Test Company",
        "location": "Hyderabad, TelanganaIndia",
        "job_url": "https://example.com/2",
        "education": r"B\.?E\., Master(?:'s)?",
    },
)


# ============================================================
# TEST 3 — LINKEDIN POSTING METADATA
# ============================================================

test_case(
    "TEST 3 - LinkedIn metadata",
    {
        "job_id": "test_3",
        "job_title": "Data Analyst",
        "company_name": "DHL Global Forwarding",
        "city": "Mumbai Metropolitan Region 48 minutes ago 46 applicants",
        "state": "",
        "country": "",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://example.com/3",
        "education": "B.?A",
    },
)


# ============================================================
# TEST 4 — SEPARATE CONTAMINATED FIELDS
# ============================================================

test_case(
    "TEST 4 - Separate contaminated fields",
    {
        "job_id": "test_4",
        "job_title": "Data Analyst",
        "company_name": "Revantage, A Blackstone Portfolio Company",
        "city": "Revantage Bengaluru",
        "state": "A Blackstone Portfolio Company Bengaluru",
        "country": "Karnataka, India",
        "location": "Bengaluru, Karnataka, India",
        "job_url": "https://example.com/4",
        "education": "B.E., Bachelor's, degree",
    },
)


# ============================================================
# TEST 5 — STATE MISTAKEN AS CITY
# ============================================================

test_case(
    "TEST 5 - State mistaken as city",
    {
        "job_id": "test_5",
        "job_title": "Data Analyst",
        "company_name": "Test Company",
        "city": "Tamil Nadu",
        "state": "India",
        "country": "",
        "location": "Tamil Nadu, India",
        "job_url": "https://example.com/5",
        "education": "Bachelor's, degree",
    },
)


print("\n" + "=" * 70)
print("NORMALIZER TEST COMPLETE")
print("=" * 70)