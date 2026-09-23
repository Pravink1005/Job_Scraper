"""
repair_csv.py

Repairs the existing unified job CSV without changing:
- job_id
- source
- title
- company
- description
- skills
- links
- posted_time
- collected_at

It focuses on cleaning:
- degree_required
- city
- state
- country

The script is designed to be SAFE TO RUN MULTIPLE TIMES.
"""

from pathlib import Path
import re
import shutil

import pandas as pd

from pipeline.normalizer import _clean_education


# ============================================================
# CONFIGURATION
# ============================================================

CSV_PATH = Path("csv_output/unified_jobs.csv")
BACKUP_PATH = Path("csv_output/unified_jobs_before_repair.csv")


# ============================================================
# CONSTANTS
# ============================================================

INDIAN_STATES = {
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Delhi",
}

INDIAN_CITIES = {
    "Ahmedabad",
    "Bengaluru",
    "Bangalore",
    "Bhubaneswar",
    "Chandigarh",
    "Chennai",
    "Coimbatore",
    "Delhi",
    "Gurgaon",
    "Gurugram",
    "Hyderabad",
    "Indore",
    "Jaipur",
    "Kochi",
    "Kolkata",
    "Lucknow",
    "Mumbai",
    "Nagpur",
    "Navi Mumbai",
    "Noida",
    "Pune",
    "Surat",
    "Thane",
    "Vadodara",
    "Visakhapatnam",
    "Vijayawada",
    "Trivandrum",
    "Thiruvananthapuram",
    "Mysuru",
    "Mysore",
    "Patna",
    "Bhopal",
    "Ranchi",
    "Dehradun",
    "Guwahati",
    "Kochi",
    "Kozhikode",
    "Madurai",
    "Tiruchirappalli",
    "Trichy",
    "Salem",
    "Vellore",
}

KNOWN_LOCATION_SUFFIXES = [
    " Area",
    " Region",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    """Convert NaN/None to empty string and strip whitespace."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def normalize_spaces(value):
    """Normalize repeated whitespace."""

    value = clean_text(value)

    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def compact(value):
    """Lowercase value and remove spaces/punctuation."""

    value = clean_text(value)

    return re.sub(
        r"[^a-z0-9]",
        "",
        value.lower(),
    )


# ============================================================
# LINKEDIN METADATA CLEANING
# ============================================================

def remove_linkedin_metadata(value):
    """
    Removes LinkedIn metadata accidentally appended to location.

    Examples:

    Mumbai Metropolitan Region 48 minutes ago ...
    ->
    Mumbai Metropolitan Region

    Bengaluru 12 minutes ago 144 applicants ...
    ->
    Bengaluru
    """

    value = normalize_spaces(value)

    if not value:
        return ""

    patterns = [
        r"\s+\d+\s*minutes?\s*ago.*$",
        r"\s+\d+\s*hours?\s*ago.*$",
        r"\s+\d+\s*days?\s*ago.*$",
        r"\s+\d+\s*weeks?\s*ago.*$",

        # Handles malformed scraped values
        r"\s+\d+\s*minutesago.*$",
        r"\s+\d+\s*hoursago.*$",
        r"\s+\d+\s*daysago.*$",

        # Applicant metadata
        r"\s+\d+\s*applicants?.*$",
        r"\s+over\s+\d+\s*applicants?.*$",
        r"\s+be\s+among.*$",
        r"\s+beamong.*$",
        r"\s+see\s+who.*$",
    ]

    for pattern in patterns:
        value = re.sub(
            pattern,
            "",
            value,
            flags=re.IGNORECASE,
        )

    return normalize_spaces(value)


# ============================================================
# COMPANY PREFIX CLEANING
# ============================================================

def remove_company_prefix(value, company):
    """
    Removes company accidentally inserted at beginning of
    location.

    Examples:

    Crunchyroll Hyderabad
    -> Hyderabad

    GLOBELANCE Gurugram
    -> Gurugram

    StateStreet Bengaluru
    -> Bengaluru

    Capco Mumbai
    -> Mumbai
    """

    value = normalize_spaces(value)
    company = normalize_spaces(company)

    if not value or not company:
        return value

    # Direct prefix
    if value.lower().startswith(company.lower()):

        remainder = value[len(company):].strip()

        if remainder:
            return remainder

    # Compare without spaces/punctuation
    company_compact = compact(company)
    value_compact = compact(value)

    if (
        company_compact
        and value_compact.startswith(company_compact)
    ):

        remainder_compact = value_compact[
            len(company_compact):
        ]

        if remainder_compact:

            # Try to recover common cities
            for city in sorted(
                INDIAN_CITIES,
                key=len,
                reverse=True,
            ):

                if compact(city) == remainder_compact:
                    return city

    return value


# ============================================================
# STATE / COUNTRY CLEANING
# ============================================================

def find_state(value):
    """
    Finds an Indian state inside a value.
    """

    value = normalize_spaces(value)

    if not value:
        return ""

    # Exact match first
    for state in sorted(
        INDIAN_STATES,
        key=len,
        reverse=True,
    ):
        if value.lower() == state.lower():
            return state

    # State + India
    for state in sorted(
        INDIAN_STATES,
        key=len,
        reverse=True,
    ):

        pattern = (
            rf"^{re.escape(state)}"
            rf"\s*,?\s*India$"
        )

        if re.match(
            pattern,
            value,
            flags=re.IGNORECASE,
        ):
            return state

    # TelanganaIndia / KarnatakaIndia
    compact_value = compact(value)

    for state in sorted(
        INDIAN_STATES,
        key=len,
        reverse=True,
    ):

        if compact_value == (
            compact(state) + "india"
        ):
            return state

    return ""


def clean_country(value):
    """
    Clean country values.

    Anything beginning with India followed by
    scraped metadata becomes India.
    """

    value = remove_linkedin_metadata(value)

    if not value:
        return ""

    compact_value = compact(value)

    if compact_value == "india":
        return "India"

    if compact_value.startswith("india"):
        return "India"

    return value


# ============================================================
# CITY CLEANING
# ============================================================

def clean_city(city, company):
    """
    General city cleanup.
    """

    city = normalize_spaces(city)

    if not city:
        return ""

    # Remove LinkedIn metadata
    city = remove_linkedin_metadata(city)

    # Remove company prefix
    city = remove_company_prefix(
        city,
        company,
    )

    # Remove accidental leading/trailing punctuation
    city = city.strip(" ,|-")

    return normalize_spaces(city)


# ============================================================
# LOCATION NORMALIZATION
# ============================================================

def normalize_linkedin_location(row):
    """
    Safely normalize LinkedIn city/state/country.

    Does NOT guess state from city unless the city is
    explicitly a state.
    """

    company = clean_text(
        row.get("company")
    )

    city = clean_city(
        row.get("city"),
        company,
    )

    state = remove_linkedin_metadata(
        row.get("state")
    )

    country = clean_country(
        row.get("country")
    )

    state = normalize_spaces(state)

    # --------------------------------------------------------
    # Company prefix accidentally inside state
    # --------------------------------------------------------

    state = remove_company_prefix(
        state,
        company,
    )

    # --------------------------------------------------------
    # State detection
    # --------------------------------------------------------

    detected_state = find_state(state)

    if detected_state:
        state = detected_state

    # --------------------------------------------------------
    # City itself is a state
    # --------------------------------------------------------

    detected_city_state = find_state(city)

    if detected_city_state:

        city = ""
        state = detected_city_state
        country = "India"

    # --------------------------------------------------------
    # City = India
    # --------------------------------------------------------

    elif city.lower() == "india":

        city = ""
        country = "India"

    # --------------------------------------------------------
    # State = India
    # --------------------------------------------------------

    if state.lower() == "india":

        state = ""
        country = "India"

    # --------------------------------------------------------
    # Country = India
    # --------------------------------------------------------

    country = clean_country(country)

    # --------------------------------------------------------
    # If country is empty but state explicitly exists
    #
    # We can safely mark India because this repair is
    # specifically for Indian job records.
    # --------------------------------------------------------

    if state and not country:
        country = "India"

    return pd.Series(
        {
            "city": city,
            "state": state,
            "country": country,
        }
    )


# ============================================================
# NAUKRI LOCATION NORMALIZATION
# ============================================================

def normalize_naukri_location(row):
    """
    Conservative Naukri cleanup.

    Naukri's location format is different from LinkedIn,
    so we avoid aggressive inference.
    """

    city = normalize_spaces(
        row.get("city")
    )

    state = normalize_spaces(
        row.get("state")
    )

    country = clean_country(
        row.get("country")
    )

    # --------------------------------------------------------
    # Remove obvious LinkedIn-style metadata if present
    # --------------------------------------------------------

    city = remove_linkedin_metadata(city)
    state = remove_linkedin_metadata(state)

    # --------------------------------------------------------
    # If city is exactly India
    # --------------------------------------------------------

    if city.lower() == "india":

        city = ""

        if not state:
            state = ""

        country = "India"

    # --------------------------------------------------------
    # Preserve valid Naukri hybrid locations
    # --------------------------------------------------------

    # Examples:
    # Hybrid - Hyderabad
    # Hybrid - Bengaluru
    # Mumbai (All Areas)

    # Do not split these automatically.

    # --------------------------------------------------------
    # If state is exactly India
    # --------------------------------------------------------

    if state.lower() == "india":

        state = ""
        country = "India"

    # --------------------------------------------------------
    # If country is empty and this is a Naukri India record
    # --------------------------------------------------------

    if not country:
        country = "India"

    return pd.Series(
        {
            "city": city,
            "state": state,
            "country": country,
        }
    )


# ============================================================
# EDUCATION REPAIR
# ============================================================

def repair_education(value):
    """
    Apply the project's education cleaner.

    Also handles a few leftover literal regex fragments.
    """

    value = clean_text(value)

    if not value:
        return "Not Specified"

    value = _clean_education(value)

    # Literal leftovers
    value = value.replace(
        "B.?A",
        "B.A.",
    )

    value = value.replace(
        "B.?A.",
        "B.A.",
    )

    value = value.replace(
        "M.?A",
        "M.A.",
    )

    value = value.replace(
        "M.?A.",
        "M.A.",
    )

    # Remove accidental regex fragments
    value = value.replace(
        "(?:",
        "",
    )

    value = value.replace(
        ")?",
        "",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"\s*,\s*",
        ", ",
        value,
    )

    return value.strip(" ,")


# ============================================================
# MAIN REPAIR
# ============================================================

def repair_csv():

    print("=" * 70)
    print("SAFE UNIFIED CSV REPAIR")
    print("=" * 70)

    # --------------------------------------------------------
    # Check input
    # --------------------------------------------------------

    if not CSV_PATH.exists():

        print(
            f"\nERROR: CSV not found:"
            f" {CSV_PATH}"
        )

        return

    # --------------------------------------------------------
    # Create backup
    # --------------------------------------------------------

    print("\nCreating backup...")

    shutil.copy2(
        CSV_PATH,
        BACKUP_PATH,
    )

    print(
        f"Backup:"
        f" {BACKUP_PATH}"
    )

    # --------------------------------------------------------
    # Read
    # --------------------------------------------------------

    df = pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False,
    )

    original_rows = len(df)

    print(
        f"\nRows loaded: {original_rows}"
    )

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "job_id",
        "source",
        "title",
        "company",
        "city",
        "state",
        "country",
        "degree_required",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        print(
            "\nERROR: Missing columns:"
        )

        for column in missing:
            print(
                f"  - {column}"
            )

        return

    # ========================================================
    # EDUCATION
    # ========================================================

    print("\n[1/4] Repairing education...")

    df["degree_required"] = (
        df["degree_required"]
        .apply(repair_education)
    )

    # ========================================================
    # SOURCE
    # ========================================================

    print("\n[2/4] Cleaning source values...")

    df["source"] = (
        df["source"]
        .apply(normalize_spaces)
    )

    # ========================================================
    # LINKEDIN LOCATIONS
    # ========================================================

    print("\n[3/4] Repairing LinkedIn locations...")

    linkedin_mask = (
        df["source"]
        .str.lower()
        .eq("linkedin")
    )

    linkedin_count = int(
        linkedin_mask.sum()
    )

    print(
        f"LinkedIn rows: {linkedin_count}"
    )

    if linkedin_count:

        cleaned_locations = (
            df.loc[
                linkedin_mask
            ]
            .apply(
                normalize_linkedin_location,
                axis=1,
            )
        )

        df.loc[
            linkedin_mask,
            [
                "city",
                "state",
                "country",
            ]
        ] = cleaned_locations

    # ========================================================
    # NAUKRI LOCATIONS
    # ========================================================

    print("\n[4/4] Repairing Naukri locations...")

    naukri_mask = (
        df["source"]
        .str.lower()
        .eq("naukri")
    )

    naukri_count = int(
        naukri_mask.sum()
    )

    print(
        f"Naukri rows: {naukri_count}"
    )

    if naukri_count:

        cleaned_locations = (
            df.loc[
                naukri_mask
            ]
            .apply(
                normalize_naukri_location,
                axis=1,
            )
        )

        df.loc[
            naukri_mask,
            [
                "city",
                "state",
                "country",
            ]
        ] = cleaned_locations

    # ========================================================
    # FINAL BASIC CLEANING
    # ========================================================

    for column in [
        "city",
        "state",
        "country",
    ]:

        df[column] = (
            df[column]
            .apply(normalize_spaces)
        )

    # ========================================================
    # PROTECT ROW COUNT
    # ========================================================

    if len(df) != original_rows:

        print(
            "\nERROR:"
            " Row count changed!"
        )

        print(
            f"Before: {original_rows}"
        )

        print(
            f"After : {len(df)}"
        )

        print(
            "\nCSV was NOT saved."
        )

        return

    # ========================================================
    # SAVE
    # ========================================================

    df.to_csv(
        CSV_PATH,
        index=False,
    )

    print(
        "\nCSV saved successfully."
    )

    print(
        f"Rows: {len(df)}"
    )

    # ========================================================
    # VALIDATION 1 — ROW COUNT
    # ========================================================

    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print(
        f"\nRow count: {len(df)}"
    )

    # ========================================================
    # VALIDATION 2 — JOB IDs
    # ========================================================

    duplicate_ids = (
        df["job_id"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate job IDs: {duplicate_ids}"
    )

    # ========================================================
    # VALIDATION 3 — EDUCATION REGEX
    # ========================================================

    education_bad = (
        df["degree_required"]
        .astype(str)
        .str.contains(
            r"\(\?:|\)\?|\\\.",
            regex=True,
            na=False,
        )
    )

    print(
        "Education regex contamination:"
        f" {education_bad.sum()}"
    )

    if education_bad.any():

        print("\nProblematic education values:")

        print(
            df.loc[
                education_bad,
                [
                    "title",
                    "company",
                    "degree_required",
                ],
            ]
            .to_string(index=False)
        )

    # ========================================================
    # VALIDATION 4 — LINKEDIN METADATA
    # ========================================================

    linkedin_bad = (
        linkedin_mask
        & df["city"].str.contains(
            r"\d+\s*minutes?\s*ago"
            r"|\d+\s*hours?\s*ago"
            r"|\d+\s*days?\s*ago"
            r"|applicants"
            r"|see who",
            case=False,
            regex=True,
            na=False,
        )
    )

    print(
        "LinkedIn metadata in city:"
        f" {linkedin_bad.sum()}"
    )

    # ========================================================
    # VALIDATION 5 — COUNTRY
    # ========================================================

    india_count = (
        df["country"]
        .str.lower()
        .eq("india")
        .sum()
    )

    print(
        f"Country = India rows: {india_count}"
    )

    # ========================================================
    # LOCATION SAMPLE
    # ========================================================

    print("\n" + "=" * 70)
    print("LOCATION SAMPLE")
    print("=" * 70)

    print(
        df[
            [
                "source",
                "company",
                "city",
                "state",
                "country",
            ]
        ]
        .head(50)
        .to_string(index=False)
    )

    # ========================================================
    # SOURCE SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("SOURCE SUMMARY")
    print("=" * 70)

    print(
        df["source"]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print("\n" + "=" * 70)

    if (
        len(df) == original_rows
        and education_bad.sum() == 0
        and linkedin_bad.sum() == 0
    ):

        print(
            "REPAIR COMPLETED SUCCESSFULLY"
        )

    else:

        print(
            "REPAIR COMPLETED WITH WARNINGS"
        )

    print("=" * 70)


if __name__ == "__main__":
    repair_csv()