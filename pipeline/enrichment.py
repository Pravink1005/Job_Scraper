"""
Shared ML enrichment step.

This module connects UnifiedJob with the existing ml_predictor.py.

IMPORTANT:
    ml/ml_predictor.py is intentionally NOT modified.

The enrichment step can fill:

    degree_required
    specialization_required

when those values are missing and a usable job description exists.

If ML is unavailable or prediction fails, the original job is returned
without breaking the pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


# ============================================================
# IMPORT UNIFIED SCHEMA
# ============================================================

from .schema import UnifiedJob


# ============================================================
# ML MODULE LOCATION
# ============================================================

ML_DIR = (
    Path(__file__).resolve().parent.parent / "ml"
)

if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))


# ============================================================
# ML IMPORT
# ============================================================

try:
    from ml_predictor import predict_job_details

    _ML_AVAILABLE = True
    _ML_IMPORT_ERROR = None

except Exception as error:  # pragma: no cover
    predict_job_details = None
    _ML_AVAILABLE = False
    _ML_IMPORT_ERROR = error


# ============================================================
# EMPTY / MISSING VALUES
# ============================================================

_UNSET_VALUES = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "not specified",
    "not_specified",
    "not available",
    "not_available",
}


# ============================================================
# PUBLIC ML STATUS
# ============================================================

def ml_available() -> bool:
    """
    Return True when ml_predictor.py was imported successfully.
    """

    return _ML_AVAILABLE


# ============================================================
# VALUE HELPERS
# ============================================================

def _is_unset(value: Any) -> bool:
    """
    Check whether a value is effectively missing.
    """

    if value is None:
        return True

    text = str(value).strip().lower()

    return text in _UNSET_VALUES


def _clean_prediction(
    value: Any,
) -> str | None:
    """
    Convert an ML prediction into a safe string.

    Empty or placeholder predictions are rejected.

    Returns:
        Clean prediction string
        or None when prediction is unusable.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.lower() in _UNSET_VALUES:
        return None

    return text


# ============================================================
# ENRICHMENT
# ============================================================

def enrich_job(
    job: UnifiedJob,
) -> UnifiedJob:
    """
    Enrich a UnifiedJob using the existing ML predictor.

    ML is only used when:

        1. ML is available
        2. degree_required OR specialization_required is missing
        3. full_description contains usable text

    Existing valid values are NEVER overwritten.

    Any ML error is handled safely and the original job is returned.
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(
        job,
        UnifiedJob,
    ):
        raise TypeError(
            "enrich_job() expects a UnifiedJob instance."
        )

    # --------------------------------------------------------
    # ML unavailable
    # --------------------------------------------------------

    if not _ML_AVAILABLE:
        return job

    # --------------------------------------------------------
    # Determine missing fields
    # --------------------------------------------------------

    needs_degree = _is_unset(
        job.degree_required
    )

    needs_specialization = _is_unset(
        job.specialization_required
    )

    # Nothing to enrich
    if not (
        needs_degree
        or needs_specialization
    ):
        return job

    # --------------------------------------------------------
    # Validate description
    # --------------------------------------------------------

    description = (
        str(
            job.full_description
            or ""
        ).strip()
    )

    if not description:
        return job

    if description.lower() in {
        "n/a",
        "not specified",
        "none",
        "null",
    }:
        return job

    # --------------------------------------------------------
    # Run ML prediction
    # --------------------------------------------------------

    try:

        predictions = predict_job_details(
            description
        )

    except Exception as error:

        print(
            "[Enrichment Warning] "
            f"ML prediction failed for job "
            f"{job.job_id}: {error}"
        )

        return job

    # --------------------------------------------------------
    # Validate prediction object
    # --------------------------------------------------------

    if not isinstance(
        predictions,
        dict,
    ):
        print(
            "[Enrichment Warning] "
            f"Unexpected ML prediction format "
            f"for job {job.job_id}"
        )

        return job

    # --------------------------------------------------------
    # Degree prediction
    # --------------------------------------------------------

    if needs_degree:

        predicted_degree = _clean_prediction(
            predictions.get(
                "predicted_degree"
            )
        )

        if predicted_degree:
            job.degree_required = (
                predicted_degree
            )

    # --------------------------------------------------------
    # Specialization prediction
    # --------------------------------------------------------

    if needs_specialization:

        predicted_specialization = _clean_prediction(
            predictions.get(
                "predicted_specialization"
            )
        )

        if predicted_specialization:
            job.specialization_required = (
                predicted_specialization
            )

    return job


# ============================================================
# MODULE TESTS
# ============================================================

def _run_enrichment_tests() -> None:
    """
    Lightweight tests for the enrichment layer.

    These tests do not modify ml_predictor.py.
    """

    print("=" * 70)
    print("ENRICHMENT MODULE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Test 1: ML status
    # --------------------------------------------------------

    print(
        f"[INFO] ML available: {ml_available()}"
    )

    if not ml_available():

        print(
            "[INFO] ML predictor could not be loaded."
        )

        if _ML_IMPORT_ERROR:

            print(
                "[INFO] Import reason:"
            )

            print(
                f"       {_ML_IMPORT_ERROR}"
            )

    print(
        "[PASS] ML availability check"
    )

    # --------------------------------------------------------
    # Test 2: Existing values must be preserved
    # --------------------------------------------------------

    existing_job = UnifiedJob(
        job_id="test_existing_001",
        source="LinkedIn",
        title="Data Analyst",
        company="Test Company",
        link="https://example.com/job/1",
        degree_required="B.E.",
        specialization_required="Data Science",
        full_description=(
            "Python SQL Power BI "
            "Bachelor degree required."
        ),
    )

    original_degree = (
        existing_job.degree_required
    )

    original_specialization = (
        existing_job.specialization_required
    )

    result = enrich_job(
        existing_job
    )

    assert (
        result.degree_required
        == original_degree
    )

    assert (
        result.specialization_required
        == original_specialization
    )

    print(
        "[PASS] Existing values preserved"
    )

    # --------------------------------------------------------
    # Test 3: Missing description
    # --------------------------------------------------------

    no_description_job = UnifiedJob(
        job_id="test_empty_description",
        source="Naukri",
        title="Data Analyst",
        company="Test Company",
        link="https://example.com/job/2",
        degree_required="Not Specified",
        specialization_required="Not Specified",
        full_description="Not Specified",
    )

    result = enrich_job(
        no_description_job
    )

    assert (
        result.degree_required
        == "Not Specified"
    )

    assert (
        result.specialization_required
        == "Not Specified"
    )

    print(
        "[PASS] Missing description handled"
    )

    # --------------------------------------------------------
    # Test 4: None values
    # --------------------------------------------------------

    none_job = UnifiedJob(
        job_id="test_none_values",
        source="Naukri",
        title="Data Analyst",
        company="Test Company",
        link="https://example.com/job/3",
        degree_required=None,
        specialization_required=None,
        full_description="",
    )

    result = enrich_job(
        none_job
    )

    assert result is none_job

    print(
        "[PASS] None values handled"
    )

    # --------------------------------------------------------
    # Test 5: Type validation
    # --------------------------------------------------------

    try:

        enrich_job(
            {
                "job_id": "invalid"
            }
        )

    except TypeError:

        print(
            "[PASS] Invalid input rejected"
        )

    else:

        raise AssertionError(
            "Invalid input was not rejected."
        )

    # --------------------------------------------------------
    # Test 6: Prediction cleaner
    # --------------------------------------------------------

    assert (
        _clean_prediction(
            None
        )
        is None
    )

    assert (
        _clean_prediction(
            ""
        )
        is None
    )

    assert (
        _clean_prediction(
            "Not Specified"
        )
        is None
    )

    assert (
        _clean_prediction(
            "  Data Science  "
        )
        == "Data Science"
    )

    print(
        "[PASS] Prediction validation"
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "ENRICHMENT MODULE TEST PASSED"
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    _run_enrichment_tests()