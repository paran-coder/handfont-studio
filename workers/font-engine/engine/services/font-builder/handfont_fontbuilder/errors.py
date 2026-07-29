class FontBuilderError(RuntimeError):
    """Base error for the HandFont font builder."""


class ManifestError(FontBuilderError):
    """Raised when an input manifest is invalid."""


class SvgOutlineError(FontBuilderError):
    """Raised when an SVG outline cannot be converted safely."""
