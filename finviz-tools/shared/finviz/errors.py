"""Common Finviz exceptions."""


class FinvizError(Exception):
    """Base class for Finviz helper errors."""


class FinvizConnectionError(FinvizError):
    """Raised when Finviz requests fail."""


class FinvizParseError(FinvizError):
    """Raised when a Finviz page cannot be parsed."""


class FinvizInvalidFilterError(FinvizError):
    """Raised when a filter or filter group cannot be resolved."""


class FinvizNoResultsError(FinvizError):
    """Raised when a screener query returns no rows."""
