"""Observed-Remove Set (add-wins) for the crdtmerge library."""


class ORSet:
    """An add-wins observed-remove set.

    Every replica owns a globally monotonic counter; each ``add`` mints a
    fresh tag ``(replica, counter)``.  ``remove`` only drops the tags the
    replica has already observed, so concurrent adds survive a merge.
    """

    def __init__(self, replica: str) -> None:
        raise NotImplementedError

    def add(self, elem) -> None:
        raise NotImplementedError

    def remove(self, elem) -> None:
        raise NotImplementedError

    def elements(self) -> frozenset:
        raise NotImplementedError
