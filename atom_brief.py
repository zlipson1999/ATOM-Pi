"""Deterministic, provider-neutral morning-brief schema and renderer."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from zoneinfo import ZoneInfo


class Priority(IntEnum):
    URGENT = 0
    IMPORTANT = 1
    INFORMATIONAL = 2


@dataclass(frozen=True)
class BriefItem:
    title: str
    summary: str
    source: str
    observed_at: datetime
    priority: Priority = Priority.INFORMATIONAL
    url: str = ""

    def __post_init__(self):
        if not self.title.strip() or not self.source.strip():
            raise ValueError("brief items require a title and source")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must include a timezone")


def render_brief(items: list[BriefItem], now: datetime, timezone_name: str) -> str:
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    local_now = now.astimezone(ZoneInfo(timezone_name))
    unique = {}
    for item in items:
        key = " ".join(item.title.lower().split())
        current = unique.get(key)
        if current is None or item.observed_at > current.observed_at:
            unique[key] = item
    lines = [f"# Morning brief — {local_now:%A, %B %d, %Y}", f"Generated: {local_now.isoformat()}"]
    for item in sorted(unique.values(), key=lambda value: (value.priority, value.title.lower())):
        age = local_now.astimezone(timezone.utc) - item.observed_at.astimezone(timezone.utc)
        freshness = "STALE" if age.total_seconds() > 24 * 3600 else "current"
        link = f" — {item.url}" if item.url else ""
        lines.append(
            f"- [{item.priority.name}] {item.title}: {item.summary} "
            f"(source: {item.source}; observed: {item.observed_at.isoformat()}; {freshness}){link}"
        )
    if not unique:
        lines.append(
            "- [INFORMATIONAL] No source data was available; no current claims can be made."
        )
    return "\n".join(lines)
