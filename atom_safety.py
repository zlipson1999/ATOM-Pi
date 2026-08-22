"""Small, dependency-free safety boundary for ATOM tool execution."""

import re
from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    READ_ONLY = "read_only"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PROHIBITED = "prohibited"


PROHIBITED = {"execute_trade", "transfer_money", "purchase", "change_account_security"}
CONFIRM = {
    "send_email",
    "send_message",
    "change_calendar",
    "delete_data",
    "publish",
    "write_external_file",
}


def classify_action(action: str) -> Risk:
    action = action.strip().lower()
    if action in PROHIBITED:
        return Risk.PROHIBITED
    if action in CONFIRM:
        return Risk.CONFIRMATION_REQUIRED
    return Risk.READ_ONLY


@dataclass(frozen=True)
class ActionRequest:
    action: str
    target: str = ""
    confirmed: bool = False

    def authorize(self) -> None:
        risk = classify_action(self.action)
        if risk is Risk.PROHIBITED:
            raise PermissionError(f"{self.action} is prohibited")
        if risk is Risk.CONFIRMATION_REQUIRED and not self.confirmed:
            raise PermissionError(f"{self.action} requires explicit confirmation")


_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*([^\s,;]+)")


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def untrusted_context(source: str, content: str, max_chars: int = 12000) -> str:
    """Delimit retrieved data so it cannot be confused with instructions."""
    safe_source = source.replace("\n", " ")[:240]
    return f"<untrusted source={safe_source!r}>\n{content[:max_chars]}\n</untrusted>"

