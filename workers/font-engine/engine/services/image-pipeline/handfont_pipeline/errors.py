from __future__ import annotations


class PipelineError(RuntimeError):
    """Base exception for recoverable image-pipeline failures."""


class MarkerDetectionError(PipelineError):
    """Raised when four registration markers cannot be resolved safely."""


class InputError(PipelineError):
    """Raised when an input file or page number is invalid."""
