import datetime
from dataclasses import dataclass, field
from collections import deque

MAX_ENTRIES = 10


@dataclass
class VerifyEvent:
    timestamp: datetime.datetime
    discord_user: str
    roblox_username: str
    steps: list[tuple[str, str]]  # (icon, description)
    success: bool


_log: deque[VerifyEvent] = deque(maxlen=MAX_ENTRIES)


def record(event: VerifyEvent):
    _log.appendleft(event)


def get_recent(n: int = 5) -> list[VerifyEvent]:
    return list(_log)[:n]


def clear():
    _log.clear()
