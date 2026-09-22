"""
Custom exception hierarchy used across the unified job pipeline.

Keeping these in one module lets both scrapers and the orchestrator raise
and catch specific, meaningful errors instead of bare `Exception`, and lets
tests assert on exact failure modes.
"""


class PipelineError(Exception):
    """Base class for every error raised by this project."""


class ScraperError(PipelineError):
    """
    Raised when a scraper (LinkedIn or Naukri) cannot complete its collection
    run because of a network failure, an anti-bot block, a timeout, or an
    unexpected page structure.

    This is intentionally distinct from Python's built-in exceptions so the
    orchestrator can catch *only* scraping failures and continue processing
    the other source, instead of accidentally swallowing programming errors.
    """

    def __init__(self, source: str, message: str, *, recoverable: bool = True):
        self.source = source
        self.recoverable = recoverable
        super().__init__(f"[{source}] {message}")


class DataValidationError(PipelineError):
    """
    Raised by the normalization layer when a raw record from a scraper is
    missing a required field or contains a value that cannot be safely
    normalized (e.g. no job link/URL, no title, malformed experience range).
    """

    def __init__(self, source: str, field: str, message: str):
        self.source = source
        self.field = field
        super().__init__(f"[{source}] invalid '{field}': {message}")


class StorageError(PipelineError):
    """Raised when the pipeline cannot read or write its CSV/state files."""
