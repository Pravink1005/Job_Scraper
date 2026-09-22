"""
Unified storage layer.

Responsibilities:

    UnifiedJob
        ↓
    JobStore
        ↓
    unified_jobs.csv
        +
    seen_job_ids.json

Both LinkedIn and Naukri use the same storage layer.

IMPORTANT:
    Storage does not modify job content.
    Normalization must already be completed before a job reaches here.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Iterable, Set, List

from .errors import StorageError
from .schema import UnifiedJob


# ============================================================
# CONSTANTS
# ============================================================

CSV_FILENAME = "unified_jobs.csv"
SEEN_FILENAME = "seen_job_ids.json"


# ============================================================
# JOB STORE
# ============================================================

class JobStore:
    """
    Persistent storage for normalized UnifiedJob records.

    Files:

        output_dir/
            unified_jobs.csv
            seen_job_ids.json
    """

    def __init__(
        self,
        output_dir: str | Path,
    ):
        self.output_dir = Path(
            output_dir
        )

        self.csv_path = (
            self.output_dir
            / CSV_FILENAME
        )

        self.seen_path = (
            self.output_dir
            / SEEN_FILENAME
        )

    # ========================================================
    # RESET
    # ========================================================

    def reset(self) -> None:
        """
        Delete the existing unified CSV and seen-job state.
        """

        removed = []

        for path in (
            self.csv_path,
            self.seen_path,
        ):

            if path.exists():

                try:
                    path.unlink()
                    removed.append(
                        path.name
                    )

                except OSError as error:

                    raise StorageError(
                        f"Failed to remove "
                        f"{path}: {error}"
                    ) from error

        if removed:

            print(
                "[Pipeline] Existing "
                "unified CSV/state removed."
            )

        else:

            print(
                "[Pipeline] No existing "
                "unified CSV/state found."
            )

    # ========================================================
    # LOAD SEEN IDS
    # ========================================================

    def load_seen_ids(self) -> Set[str]:
        """
        Load persistent seen job IDs.

        IDs are loaded from both:

            1. seen_job_ids.json
            2. existing unified_jobs.csv

        CSV IDs are always included so that the CSV itself
        remains a fallback source of truth if the JSON state
        becomes outdated.
        """

        seen: Set[str] = set()

        # ----------------------------------------------------
        # LOAD JSON STATE
        # ----------------------------------------------------

        if self.seen_path.exists():

            try:

                with open(
                    self.seen_path,
                    "r",
                    encoding="utf-8",
                ) as file:

                    data = json.load(
                        file
                    )

                if isinstance(
                    data,
                    list,
                ):

                    for value in data:

                        value = str(
                            value
                        ).strip()

                        if value:

                            seen.add(
                                value
                            )

                elif isinstance(
                    data,
                    set,
                ):

                    for value in data:

                        value = str(
                            value
                        ).strip()

                        if value:

                            seen.add(
                                value
                            )

                else:

                    print(
                        "[Deduplication Warning] "
                        f"{self.seen_path} "
                        "does not contain a "
                        "valid ID list."
                    )

            except (
                OSError,
                json.JSONDecodeError,
            ) as error:

                print(
                    "[Deduplication Warning] "
                    f"Could not read "
                    f"{self.seen_path}: "
                    f"{error}"
                )

        # ----------------------------------------------------
        # LOAD IDS FROM CSV
        # ----------------------------------------------------

        if self.csv_path.exists():

            try:

                with open(
                    self.csv_path,
                    "r",
                    newline="",
                    encoding="utf-8-sig",
                ) as file:

                    reader = csv.DictReader(
                        file
                    )

                    if reader.fieldnames is None:

                        print(
                            "[Deduplication Warning] "
                            f"{self.csv_path} "
                            "has no CSV header."
                        )

                    else:

                        for row in reader:

                            job_id = (
                                row.get(
                                    "job_id"
                                )
                                or ""
                            ).strip()

                            if job_id:

                                seen.add(
                                    job_id
                                )

            except (
                OSError,
                csv.Error,
            ) as error:

                print(
                    "[Deduplication Warning] "
                    f"Could not read "
                    f"{self.csv_path}: "
                    f"{error}"
                )

        return seen

    # ========================================================
    # SAVE SEEN IDS
    # ========================================================

    def save_seen_ids(
        self,
        seen_ids: Iterable[str],
    ) -> None:
        """
        Persist seen job IDs atomically.

        The temporary file is replaced only after the complete
        JSON file has been written successfully.
        """

        try:

            self.output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            clean_ids = {
                str(job_id).strip()
                for job_id in seen_ids
                if job_id is not None
                and str(job_id).strip()
            }

            temp_path = Path(
                f"{self.seen_path}.tmp"
            )

            with open(
                temp_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    sorted(clean_ids),
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

                file.flush()

                os.fsync(
                    file.fileno()
                )

            os.replace(
                temp_path,
                self.seen_path,
            )

        except OSError as error:

            raise StorageError(
                "Failed to persist "
                f"seen-job state: {error}"
            ) from error

    # ========================================================
    # CSV HEADER CHECK
    # ========================================================

    def _csv_needs_header(self) -> bool:
        """
        Determine whether unified_jobs.csv needs a header.
        """

        if not self.csv_path.exists():
            return True

        try:

            return (
                self.csv_path.stat().st_size
                == 0
            )

        except OSError as error:

            raise StorageError(
                f"Could not inspect "
                f"{self.csv_path}: "
                f"{error}"
            ) from error

    # ========================================================
    # VALIDATE JOB
    # ========================================================

    @staticmethod
    def _validate_job(
        job: UnifiedJob,
    ) -> bool:
        """
        Validate the object before writing it.

        Storage should receive normalized UnifiedJob objects
        only.
        """

        if not isinstance(
            job,
            UnifiedJob,
        ):

            return False

        job_id = getattr(
            job,
            "job_id",
            None,
        )

        if job_id is None:
            return False

        if not str(
            job_id
        ).strip():

            return False

        return True

    # ========================================================
    # PREPARE JOB BATCH
    # ========================================================

    def _prepare_jobs(
        self,
        jobs: Iterable[UnifiedJob],
    ) -> List[UnifiedJob]:
        """
        Validate jobs and remove duplicate job IDs from the
        current batch.

        Existing CSV/JSON deduplication is handled by the
        orchestrator through load_seen_ids().
        """

        prepared: List[
            UnifiedJob
        ] = []

        batch_ids: Set[str] = set()

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            # ------------------------------------------------
            # TYPE CHECK
            # ------------------------------------------------

            if not self._validate_job(
                job
            ):

                print(
                    "[Storage Warning] "
                    f"Skipping invalid job "
                    f"at batch position "
                    f"{index}."
                )

                continue

            # ------------------------------------------------
            # JOB ID
            # ------------------------------------------------

            job_id = str(
                job.job_id
            ).strip()

            # ------------------------------------------------
            # DUPLICATE WITHIN BATCH
            # ------------------------------------------------

            if job_id in batch_ids:

                print(
                    "[Storage Warning] "
                    f"Skipping duplicate "
                    f"job_id={job_id}"
                )

                continue

            batch_ids.add(
                job_id
            )

            prepared.append(
                job
            )

        return prepared

    # ========================================================
    # APPEND JOBS
    # ========================================================

    def append_jobs(
        self,
        jobs: Iterable[UnifiedJob],
    ) -> int:
        """
        Append normalized jobs to unified_jobs.csv.

        A CSV header is written only when:

            - the file does not exist, or
            - the file is empty.

        Returns:
            Number of rows successfully prepared/written.
        """

        jobs = self._prepare_jobs(
            jobs
        )

        if not jobs:
            return 0

        try:

            self.output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            needs_header = (
                self._csv_needs_header()
            )

            fieldnames = (
                UnifiedJob.fieldnames()
            )

            with open(
                self.csv_path,
                "a",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=fieldnames,
                    extrasaction="ignore",
                )

                if needs_header:

                    writer.writeheader()

                for job in jobs:

                    row = job.to_csv_row()

                    writer.writerow(
                        row
                    )

                file.flush()

                os.fsync(
                    file.fileno()
                )

        except (
            OSError,
            csv.Error,
        ) as error:

            raise StorageError(
                f"Failed to write "
                f"{self.csv_path}: "
                f"{error}"
            ) from error

        return len(jobs)

    # ========================================================
    # STORAGE STATUS
    # ========================================================

    def exists(self) -> bool:
        """
        Return True when the unified CSV exists.
        """

        return self.csv_path.exists()

    def count_rows(self) -> int:
        """
        Count data rows currently stored in the unified CSV.

        The header is not counted.
        """

        if not self.csv_path.exists():
            return 0

        count = 0

        try:

            with open(
                self.csv_path,
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                reader = csv.DictReader(
                    file
                )

                for row in reader:

                    if row:

                        count += 1

        except (
            OSError,
            csv.Error,
        ) as error:

            raise StorageError(
                f"Failed to count rows "
                f"in {self.csv_path}: "
                f"{error}"
            ) from error

        return count


# ============================================================
# MODULE TEST
# ============================================================

def _run_storage_tests() -> None:
    """
    Lightweight storage module test.

    Uses a temporary directory and does not touch the real
    csv_output directory.
    """

    import tempfile

    print("=" * 70)
    print("STORAGE MODULE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Create temporary storage
    # --------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        store = JobStore(
            temp_dir
        )

        # ----------------------------------------------------
        # Initially empty
        # ----------------------------------------------------

        assert (
            store.exists()
            is False
        )

        assert (
            store.count_rows()
            == 0
        )

        assert (
            store.load_seen_ids()
            == set()
        )

        print(
            "[PASS] Empty storage"
        )

        # ----------------------------------------------------
        # Create test UnifiedJob
        # ----------------------------------------------------

        job = UnifiedJob(
            job_id="linkedin_test_001",
            source="LinkedIn",
            title="Data Analyst",
            company="Test Company",
            category="Data Analytics",
            city="Hyderabad",
            state="Telangana",
            country="India",
            min_experience_years="2",
            max_experience_years="5",
            salary="Not specified",
            skills="Python, SQL",
            degree_required="B.E.",
            specialization_required="Data Science",
            posted_time="2 hours ago",
            collected_at="2026-09-22 10:00:00",
            link="https://example.com/job/1",
            full_description="Test job description",
        )

        # ----------------------------------------------------
        # Write first job
        # ----------------------------------------------------

        written = store.append_jobs(
            [job]
        )

        assert written == 1

        assert (
            store.exists()
            is True
        )

        assert (
            store.count_rows()
            == 1
        )

        print(
            "[PASS] First CSV write"
        )

        # ----------------------------------------------------
        # Duplicate in same batch
        # ----------------------------------------------------

        written = store.append_jobs(
            [
                job,
                job,
            ]
        )

        assert written == 1

        assert (
            store.count_rows()
            == 2
        )

        print(
            "[PASS] Batch duplicate protection"
        )

        # ----------------------------------------------------
        # Load seen IDs from CSV
        # ----------------------------------------------------

        seen = (
            store.load_seen_ids()
        )

        assert (
            "linkedin_test_001"
            in seen
        )

        print(
            "[PASS] CSV seen-ID recovery"
        )

        # ----------------------------------------------------
        # Save JSON state
        # ----------------------------------------------------

        store.save_seen_ids(
            seen
        )

        assert (
            store.seen_path.exists()
        )

        loaded = (
            store.load_seen_ids()
        )

        assert (
            "linkedin_test_001"
            in loaded
        )

        print(
            "[PASS] JSON seen-ID persistence"
        )

        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        store.reset()

        assert (
            store.exists()
            is False
        )

        assert (
            store.seen_path.exists()
            is False
        )

        print(
            "[PASS] Storage reset"
        )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "STORAGE MODULE TEST PASSED"
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    _run_storage_tests()