"""Core data types. Everything here is synthetic and declared, not calibrated on survey data."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    CAR = "car"
    BUS = "bus"
    BIKE = "bike"
    WALK = "walk"


# Modes in which an adult can accompany a young child (no child seat on bikes in this model).
ESCORT_MODES = (Mode.CAR, Mode.BUS, Mode.WALK)

# Declared generalized-cost assumptions (minutes-equivalent). Illustrative, NOT estimated.
MONEY_EUR = {Mode.CAR: 4.0, Mode.BUS: 1.9, Mode.BIKE: 0.0, Mode.WALK: 0.0}
MIN_PER_EUR = 3.0          # value of one euro in minutes
LATE_WEIGHT = 4.0          # one minute late costs four minutes of travel
MISSED_PENALTY = 90.0      # activity not reached, or reached more than MISSED_LATENESS late
MISSED_LATENESS = 30
CHILD_MISSED_PENALTY = 240.0  # a young child left at home / >30 min late: a duty, weighted well above an adult's lost activity
REPLAN_DELAY = 5           # minutes lost when a planned car is not there at departure
BROKEN_CAR_DELAY = 10      # minutes lost discovering the car will not start
DUPLICATE_ESCORT_DELAY = 3
WASTED_ESCORT_EXTRA = 10   # going to a closed school and back


def clock(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


@dataclass
class Member:
    id: str
    name: str
    role: str
    age: int
    destination: str
    zone: str
    ready: int                      # earliest departure (minutes after midnight)
    deadline: int                   # latest acceptable arrival
    base: dict[Mode, int]           # normal-day door-to-door minutes (accompanied time for young children)
    can_drive: bool = False
    can_bike: bool = True
    needs_escort: bool = False
    prefs: dict[Mode, float] = field(default_factory=dict)   # minutes-equivalent, negative = liked
    habit: str = ""

    @property
    def is_agent(self) -> bool:
        """Members who decide for themselves. Young children are passive but can send requests."""
        return not self.needs_escort

    def solo_modes(self) -> list[Mode]:
        if self.needs_escort:
            return []
        return [m for m in Mode if m in self.base
                and (m != Mode.CAR or self.can_drive) and (m != Mode.BIKE or self.can_bike)]


@dataclass
class Household:
    id: str
    name: str
    description: str
    members: list[Member]
    n_cars: int
    routine_escort: dict[str, str]                 # child id -> adult id who usually accompanies
    detour: dict[str, dict[str, dict[Mode, int]]]  # adult -> child -> mode -> extra minutes

    def member(self, mid: str) -> Member:
        return next(m for m in self.members if m.id == mid)

    @property
    def agents(self) -> list[Member]:
        return [m for m in self.members if m.is_agent]

    @property
    def children(self) -> list[Member]:
        return [m for m in self.members if m.needs_escort]


@dataclass(frozen=True)
class Effect:
    """Ground-truth consequence of an event. `kind` is one of:
    delay (mode +amount min), unavailable (mode), cars_down (amount cars), deadline (member +amount),
    no_trip (member), pref (mode +amount discomfort)."""
    kind: str
    mode: Mode | None = None
    zone: str | None = None        # restrict to members whose destination zone matches
    member: str | None = None
    amount: int = 0


@dataclass
class Event:
    id: str
    label: str
    # none: nothing happens; structured: published on official channels, so the journey planner
    # already reflects it; unstructured: only available as free text; decoy: irrelevant free text.
    kind: str
    text: str
    effects: list[Effect] = field(default_factory=list)

    @property
    def is_text_only(self) -> bool:
        return self.kind in ("unstructured", "decoy")


@dataclass(frozen=True)
class Option:
    id: str
    member: str
    mode: Mode | None              # None = do not travel today
    escort: str | None = None      # child id accompanied on the way

    def describe(self, hh: Household) -> str:
        if self.mode is None:
            return "stay at home"
        if self.escort:
            return f"{self.mode.value}, accompanying {hh.member(self.escort).name}"
        return f"{self.mode.value} alone"


@dataclass
class Message:
    round: int
    sender: str
    receiver: str                  # member id or "all"
    performative: str              # inform | request | propose | counter | accept | reject | commit
    content: dict[str, Any]
    text: str
    source: str                    # rule | llm | fallback | protocol | environment

    def as_dict(self) -> dict[str, Any]:
        return {"round": self.round, "sender": self.sender, "receiver": self.receiver,
                "performative": self.performative, "content": self.content, "text": self.text,
                "source": self.source}
