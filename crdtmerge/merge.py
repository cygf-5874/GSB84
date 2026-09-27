"""Merge, canonical serialization and decoding for the crdtmerge library."""


def merge(a, b):
    """Return a new CRDT holding the join of ``a`` and ``b``."""
    raise NotImplementedError


def state(obj) -> bytes:
    """Return the canonical byte encoding of ``obj``."""
    raise NotImplementedError


def load(blob: bytes):
    """Rebuild a CRDT object from its canonical byte encoding."""
    raise NotImplementedError
