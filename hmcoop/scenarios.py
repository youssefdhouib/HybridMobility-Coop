"""Synthetic households and morning events.

Zone names evoke Toulouse districts for readability only; travel times are invented and are NOT
derived from the EMC2 survey, GTFS or OpenTripPlanner.
"""
from __future__ import annotations

import copy
import random
from typing import Callable

from .model import Effect, Event, Household, Member, Mode, clock

C, B, K, W = Mode.CAR, Mode.BUS, Mode.BIKE, Mode.WALK


def _t(h: int, m: int = 0) -> int:
    return h * 60 + m


def _households() -> dict[str, Household]:
    hh = [
        Household(
            "martin", "Martin family", "Two working parents, an 8-year-old and a teenager; ONE car.",
            [
                Member("marie", "Marie", "nurse", 39, "Purpan hospital", "Purpan", _t(7, 0), _t(7, 45),
                       {C: 25, B: 35, K: 50, W: 80}, can_drive=True, habit="usually takes the bus to the hospital"),
                Member("paul", "Paul", "aerospace engineer", 41, "aerospace site", "Blagnac", _t(7, 40), _t(8, 30),
                       {C: 30, B: 50, K: 40, W: 110}, can_drive=True, prefs={B: 10},
                       habit="usually drives the car and drops Lea at school on the way"),
                Member("lea", "Lea", "pupil", 8, "Jules-Ferry primary school", "Centre", _t(7, 45), _t(8, 20),
                       {C: 10, B: 15, W: 20}, needs_escort=True),
                Member("tom", "Tom", "high-school student", 16, "Rangueil high school", "Rangueil", _t(7, 20), _t(8, 0),
                       {B: 25, K: 22, W: 50}, prefs={K: -5}, habit="usually cycles to school"),
            ],
            n_cars=1, routine_escort={"lea": "paul"},
            detour={"paul": {"lea": {C: 8, B: 20, W: 25}}, "marie": {"lea": {C: 10, B: 22, W: 25}}},
        ),
        Household(
            "dubois", "Dubois family", "Two parents with TWO cars and a 6-year-old.",
            [
                Member("claire", "Claire", "lawyer", 36, "law courts", "Centre", _t(8, 0), _t(8, 45),
                       {C: 20, B: 25, K: 20, W: 45}, can_drive=True, prefs={C: -5},
                       habit="usually drives and drops Noah at nursery school"),
                Member("marc", "Marc", "maintenance technician", 38, "industrial park", "Labege", _t(7, 30), _t(8, 15),
                       {C: 25, B: 45, K: 45, W: 120}, can_drive=True, habit="usually drives to work"),
                Member("noah", "Noah", "nursery pupil", 6, "Saint-Aubin nursery school", "Centre", _t(7, 50), _t(8, 30),
                       {C: 8, B: 12, W: 15}, needs_escort=True),
            ],
            n_cars=2, routine_escort={"noah": "claire"},
            detour={"claire": {"noah": {C: 5, B: 8, W: 5}}, "marc": {"noah": {C: 15, B: 25, W: 20}}},
        ),
        Household(
            "benali", "Benali family", "Single parent, a 7-year-old and a 14-year-old; ONE car.",
            [
                Member("samira", "Samira", "pharmacist", 42, "pharmacy", "Compans", _t(7, 45), _t(8, 45),
                       {C: 20, B: 30, K: 25, W: 50}, can_drive=True,
                       habit="usually drives and drops Yanis at school"),
                Member("yanis", "Yanis", "pupil", 7, "Minimes primary school", "Minimes", _t(7, 45), _t(8, 20),
                       {C: 8, B: 15, W: 18}, needs_escort=True),
                Member("ines", "Ines", "middle-school student", 14, "Minimes middle school", "Minimes", _t(7, 30), _t(8, 15),
                       {B: 20, K: 15, W: 30}, habit="usually walks to school with friends"),
            ],
            n_cars=1, routine_escort={"yanis": "samira"},
            detour={"samira": {"yanis": {C: 6, B: 15, W: 20}}, "ines": {"yanis": {B: 5, W: 3}}},
        ),
        Household(
            "flatshare", "Flatshare", "Three working flatmates sharing ONE car; no children.",
            [
                Member("julien", "Julien", "software developer", 29, "tech park", "Labege", _t(7, 30), _t(8, 30),
                       {C: 25, B: 50, K: 40, W: 120}, can_drive=True, habit="usually drives the shared car"),
                Member("sofia", "Sofia", "logistics planner", 31, "airport logistics hub", "Blagnac", _t(7, 45), _t(8, 30),
                       {C: 30, B: 55, K: 45, W: 130}, can_drive=True, prefs={C: -5}, habit="usually takes the bus"),
                Member("amine", "Amine", "PhD student", 27, "university lab", "Rangueil", _t(8, 0), _t(9, 0),
                       {C: 15, B: 25, K: 20, W: 45}, can_drive=True, prefs={K: -5}, habit="usually cycles"),
            ],
            n_cars=1, routine_escort={}, detour={},
        ),
        Household(
            "garcia", "Garcia family", "Grandmother (only driver), a parent without licence, a 9-year-old; ONE car.",
            [
                Member("rosa", "Rosa", "retired volunteer", 66, "community association", "Mirail", _t(8, 0), _t(9, 30),
                       {C: 15, B: 30, W: 40}, can_drive=True, can_bike=False,
                       habit="usually drives Lucas to school, then goes to the association"),
                Member("david", "David", "cook", 38, "restaurant", "Centre", _t(7, 30), _t(8, 30),
                       {B: 25, K: 20, W: 45}, habit="usually cycles to the restaurant"),
                Member("lucas", "Lucas", "pupil", 9, "Mirail primary school", "Mirail", _t(8, 0), _t(8, 30),
                       {C: 7, B: 15, W: 20}, needs_escort=True),
            ],
            n_cars=1, routine_escort={"lucas": "rosa"},
            detour={"rosa": {"lucas": {C: 3, B: 5, W: 5}}, "david": {"lucas": {B: 25, W: 30}}},
        ),
    ]
    return {h.id: h for h in hh}


# Who each household-specific event targets (fixed in advance, not chosen by any policy).
TARGETS = {
    "martin": {"zone": "Blagnac", "deadline": "marie", "no_trip": "lea"},
    "dubois": {"zone": "Labege", "deadline": "claire", "no_trip": "noah"},
    "benali": {"zone": "Compans", "deadline": "samira", "no_trip": "yanis"},
    "flatshare": {"zone": "Labege", "deadline": "sofia", "no_trip": "amine"},
    "garcia": {"zone": "Mirail", "deadline": "david", "no_trip": "lucas"},
}

HOUSEHOLDS = _households()


def _none(hh: Household) -> Event:
    return Event("none", "Ordinary day", "none", "")


def _bus_strike(hh: Household) -> Event:
    return Event("bus_strike", "Bus strike (official)", "structured",
                 "Official notice from the city bus operator: strike, no bus service this morning.",
                 [Effect("unavailable", mode=B)])


def _rain(hh: Household) -> Event:
    return Event("heavy_rain", "Heavy rain (official)", "structured",
                 "Weather service: heavy rain all morning; roads slower.",
                 [Effect("delay", mode=K, amount=12), Effect("delay", mode=W, amount=10),
                  Effect("delay", mode=C, amount=8), Effect("delay", mode=B, amount=6),
                  Effect("pref", mode=K, amount=15), Effect("pref", mode=W, amount=10)])


def _car_breakdown(hh: Household) -> Event:
    which = "the family car" if hh.n_cars == 1 else "the older of the two cars"
    return Event("car_breakdown", "Car warning light (text only)", "unstructured",
                 f"Last night {which} made a loud grinding noise and the engine warning light came on. "
                 "The mechanic said on the phone not to drive it until it has been checked.",
                 [Effect("cars_down", amount=1)])


def _accident(hh: Household) -> Event:
    z = TARGETS[hh.id]["zone"]
    return Event("ringroad_accident", f"Ring-road accident towards {z} (text only)", "unstructured",
                 f"Local radio, 06:55: a lorry has overturned on the ring road near the {z} exit. "
                 f"Drivers heading to {z} should expect about 40 extra minutes all morning.",
                 [Effect("delay", mode=C, zone=z, amount=40)])


def _no_trip(hh: Household) -> Event:
    m = hh.member(TARGETS[hh.id]["no_trip"])
    if m.needs_escort:
        text = (f"Text message from {m.destination} at 06:45: the school is closed today because of a "
                f"heating failure; {m.name} should stay at home.")
        label = "School closed (text only)"
    else:
        text = (f"Email to {m.name} at 06:40: the {m.destination} building is closed today (power cut); "
                "please work from home.")
        label = "Workplace closed (text only)"
    return Event("no_trip", label, "unstructured", text, [Effect("no_trip", member=m.id)])


def _deadline(hh: Household) -> Event:
    m =hh.member(TARGETS[hh.id]["deadline"])
    return Event("deadline_change", "Earlier start for one member (text only)", "unstructured",
                 f"Message to {m.name} at 06:50: today you must arrive at the {m.destination} 30 minutes "
                 f"earlier than usual, i.e. by {clock(m.deadline - 30)}.",
                 [Effect("deadline", member=m.id, amount=-30)])


def _decoy(hh: Household) -> Event:
    return Event("decoy", "Irrelevant news (negative control)", "decoy",
                 "Town hall newsletter: a street party will take place next Saturday evening, and the "
                 "Sunday market moves to the other side of the square for the summer.", [])


EVENTS: dict[str, Callable[[Household], Event]] = {
    "none": _none, "bus_strike": _bus_strike, "heavy_rain": _rain, "car_breakdown": _car_breakdown,
    "ringroad_accident": _accident, "no_trip": _no_trip, "deadline_change": _deadline, "decoy": _decoy,
}


def make_household(hid: str, seed: int = 0) -> Household:
    """Seed 0 returns the canonical household; other seeds jitter times reproducibly."""
    hh = copy.deepcopy(HOUSEHOLDS[hid])
    if seed == 0:
        return hh
    rng = random.Random(f"{hid}:{seed}")
    for m in hh.members:
        m.ready += rng.choice([-10, -5, 0, 5, 10])
        m.deadline += rng.choice([-10, -5, 0, 5, 10])
        m.base = {mode: max(3, round(v * rng.uniform(0.85, 1.15))) for mode, v in m.base.items()}
    for adult in hh.detour.values():
        for child, d in adult.items():
            adult[child] = {mode: max(1, round(v * rng.uniform(0.85, 1.15))) for mode, v in d.items()}
    return hh


def make_scenario(hid: str, event_id: str, seed: int = 0) -> tuple[Household, Event]:
    hh = make_household(hid, seed)
    # Event text references the household's own (jittered) times, e.g. the new deadline.
    return hh, EVENTS[event_id](hh)
