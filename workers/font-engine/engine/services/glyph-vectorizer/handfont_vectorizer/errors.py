from __future__ import annotations


class VectorizerError(RuntimeError):
    """Base exception for recoverable vectorizer failures."""


class InputMaskError(VectorizerError):
    """Raised when the input mask is unreadable or unsuitable."""


class EmptyMaskError(InputMaskError):
    """Raised when a batch item contains no usable foreground."""


class VectorizationError(VectorizerError):
    """Raised when no safe vector outline can be generated."""
