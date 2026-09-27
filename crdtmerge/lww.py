"""Last-Writer-Wins register for the crdtmerge library."""


class LWWRegister:
    """A last-writer-wins register keyed by ``(ts, replica)``.

    ``replica`` breaks ties by lexicographic order so that merging is
    commutative.  An unset register reads back as ``None``.
    """

    def __init__(self, replica: str) -> None:
        raise NotImplementedError

    def set(self, value, ts: int) -> None:
        raise NotImplementedError

    def value(self):
        raise NotImplementedError
