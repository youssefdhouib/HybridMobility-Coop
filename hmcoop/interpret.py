"""LLM as event interpreter (neuro-symbolic hybrid).

The LLM never chooses a travel option here. It reads the free-text news once per household and maps it onto a
fixed vocabulary of planner state changes; rules and the negotiation protocol then decide as usual. The
vocabulary is the planner's own set of state variables, so a news item outside it can only map to 'none'.
"""
from __future__ import annotations

from typing import Any

from .llm import LLMCall, OllamaClient
from .model import Effect, Event, Household, Mode

EFFECTS = {
    "none": "the news does not change this household's trips this morning",
    "car_unavailable": "the household's car (or one of its cars) must not be used today",
    "car_delay": "driving towards one district is slower; give the district and the extra minutes",
    "bus_unavailable": "there is no bus service",
    "member_no_trip": "one member's activity is cancelled today; give the member id",
    "member_earlier_deadline": "one member must arrive earlier than usual; give the member id and how many minutes earlier",
}

SYSTEM = ("You convert a free-text morning news item into ONE structured effect for a household travel planner. "
          "First copy into 'evidence' the words of the news that matter for travel this morning (or 'nothing relevant'). "
          "Then pick the effect those words imply. Answer 'none' only if the news does not affect this household's "
          "trips this morning. Answer in JSON.")

# One worked example from a household and wording that do not appear in the scenarios (prompt revision v2).
EXAMPLE = ("Example (different household):\nMembers: id=max: Max, 10, pupil, goes to the swimming pool (district Nord); "
           "id=ana: Ana, 40, teacher, goes to the college (district Sud).\n"
           "News: The swimming pool emailed at 07:00: today's lesson is cancelled because of a technical problem.\n"
           'Answer: {"evidence": "today\'s lesson is cancelled", "effect": "member_no_trip", "member": "max", '
           '"district": "none", "minutes": 0}')


def interpret(client: OllamaClient, hh: Household, event: Event) -> tuple[list[Effect], LLMCall, dict[str, Any]]:
    zones = sorted({m.zone for m in hh.members})
    ids = [m.id for m in hh.members]
    members = "\n".join(f"- id={m.id}: {m.name}, {m.age}, {m.role}, goes to the {m.destination} (district {m.zone})"
                        for m in hh.members)
    vocab = "\n".join(f"- {k}: {v}" for k, v in EFFECTS.items())
    user = (f"Possible effects:\n{vocab}\nUse member 'none' or district 'none' and minutes 0 when not applicable.\n\n"
            f"{EXAMPLE}\n\nNow this household:\nMembers:\n{members}\nThe household owns {hh.n_cars} car(s).\n"
            f"News: {event.text}\nAnswer:")
    schema = {"type": "object", "properties": {
        "evidence": {"type": "string"},
        "effect": {"type": "string", "enum": list(EFFECTS)},
        "member": {"type": "string", "enum": ids + ["none"]},
        "district": {"type": "string", "enum": zones + ["none"]},
        "minutes": {"type": "integer"}},
        "required": ["evidence", "effect", "member", "district", "minutes"]}
    call = client.chat("interpret", "household", SYSTEM, user, schema)
    if not call.ok or not call.data:
        return [], call, {"effect": "invalid", "error": call.error}
    d = call.data
    eff, member, zone = d["effect"], d["member"], d["district"]
    minutes = max(0, min(120, int(d.get("minutes") or 0)))
    out: list[Effect] = []
    if eff == "car_unavailable":
        out = [Effect("cars_down", amount=1)]
    elif eff == "car_delay" and minutes > 0:
        out = [Effect("delay", mode=Mode.CAR, zone=None if zone == "none" else zone, amount=minutes)]
    elif eff == "bus_unavailable":
        out = [Effect("unavailable", mode=Mode.BUS)]
    elif eff == "member_no_trip" and member != "none":
        out = [Effect("no_trip", member=member)]
    elif eff == "member_earlier_deadline" and member != "none" and minutes > 0:
        out = [Effect("deadline", member=member, amount=-minutes)]
    elif eff != "none":  # incomplete structured answer: validated away, logged
        return [], call, {"effect": eff, "member": member, "district": zone, "minutes": minutes,
                          "rejected": "missing member/district/minutes"}
    return out, call, {"effect": eff, "member": member, "district": zone, "minutes": minutes,
                       "evidence": str(d.get("evidence", ""))[:240]}


def matches_truth(event: Event, effects: list[Effect]) -> bool:
    """Exact-match check of the interpretation against the event's ground-truth effects (for text events)."""
    truth = sorted((e.kind, e.mode, e.zone, e.member) for e in event.effects)
    got = sorted((e.kind, e.mode, e.zone, e.member) for e in effects)
    return truth == got
