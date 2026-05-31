"""Utilities for selecting user-visible reference sources."""
from typing import Any, Iterable, List


MAX_VISIBLE_REFERENCE_SOURCES = 2


def _value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def select_reference_sources(
    sources: Iterable[Any],
    max_sources: int = MAX_VISIBLE_REFERENCE_SOURCES,
) -> List[Any]:
    """Deduplicate sources in retrieval order and return at most max_sources."""
    selected: List[Any] = []
    seen = set()

    for source in sources:
        key = (_value(source, "source"), _value(source, "title"), _value(source, "url"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(source)
        if len(selected) >= max_sources:
            break

    return selected
