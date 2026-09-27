"""Error types raised by the crdtmerge library."""


class CrdtError(Exception):
    """Base class for every error raised by crdtmerge."""


class CorruptState(CrdtError):
    """Raised when a serialized state blob cannot be decoded."""
