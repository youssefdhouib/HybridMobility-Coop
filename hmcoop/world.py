"""Environment: what agents can observe, option enumeration, joint-plan validation and execution.

Two views of the same morning exist:
  * observed: base network + effects of *structured* (officially published) events. This is what the
    journey planner shows every policy, identically.
  * truth: all effects, including those only described in free text. Execution always uses truth.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .model import (BROKEN_CAR_DELAY, CHILD_MISSED_PENALTY, DUPLICATE_ESCORT_DELAY, ESCORT_MODES, LATE_WEIGHT, MIN_PER_EUR,
                    MISSED_LATENESS, MISSED_PENALTY, MONEY_EUR, REPLAN_DELAY, WASTED_ESCORT_EXTRA,
                    Effect, Event, Household, Member, Mode, Option, clock)


class Conditions:
    def __init__(self, hh: Household, effects: list[Effect], name: str):
        self.hh, self.effects, self.name = hh, effects, name

    @classmethod
    def observed(cls, hh: Household, event: Event) -> "Conditions":
        return cls(hh, list(event.effects) if event.kind == "structured" else [], "observed")

    @classmethod
    def truth(cls, hh: Household, event: Event) -> "Conditions":
        return cls(hh, list(event.effects), "truth")

    def _match(self, e: Effect, m: Member, mode: Mode | None = None) -> bool:
        return ((e.mode is None or e.mode == mode) and (e.zone is None or e.zone == m.zone)
                and (e.member is None or e.member == m.id))

    def has_trip(self, mid: str) -> bool:
        return not any(e.kind == "no_trip" and e.member == mid for e in self.effects)

    def deadline(self, m: Member) -> int:
        return m.deadline + sum(e.amount for e in self.effects if e.kind == "deadline" and e.member == m.id)

    def available(self, m: Member, mode: Mode) -> bool:
        return mode in m.base and not any(e.kind == "unavailable" and self._match(e, m, mode)
                                          for e in self.effects)

    def minutes(self, m: Member, mode: Mode) -> int:
        return m.base[mode] + sum(e.amount for e in self.effects if e.kind == "delay" and self._match(e, m, mode))

    def pref(self, m: Member, mode: Mode) -> float:
        return m.prefs.get(mode, 0.0) + sum(e.amount for e in self.effects
                                           if e.kind == "pref" and self._match(e, m, mode))

    def cars(self) -> int:
        return max(0, self.hh.n_cars - sum(e.amount for e in self.effects if e.kind == "cars_down"))


@dataclass
class Leg:
    """Evaluation of one option for its owner under some Conditions."""
    depart: int
    arrive: int | None
    minutes: int
    late: int
    cost: float                     # owner's subjective cost (includes accompanied child's outcome)
    child_arrive: int | None = None
    child_late: int = 0
    note: str = ""


def evaluate(hh: Household, cond: Conditions, opt: Option) -> Leg:
    m = hh.member(opt.member)
    if opt.mode is None:  # stay at home
        return Leg(m.ready, None, 0, 0, MISSED_PENALTY if cond.has_trip(m.id) else 0.0, note="stays home")
    child = hh.member(opt.escort) if opt.escort else None
    child_goes = child is not None and cond.has_trip(child.id)
    depart = max(m.ready, child.ready) if child_goes else m.ready
    minutes = cond.minutes(m, opt.mode)
    if child is not None:
        minutes += hh.detour[m.id][child.id][opt.mode] + (0 if child_goes else WASTED_ESCORT_EXTRA)
    cost = minutes + cond.pref(m, opt.mode) + MONEY_EUR[opt.mode] * MIN_PER_EUR
    arrive, late = depart + minutes, 0
    if cond.has_trip(m.id):
        late = max(0, arrive - cond.deadline(m))
        cost += LATE_WEIGHT * late + (MISSED_PENALTY if late > MISSED_LATENESS else 0)
    leg = Leg(depart, arrive, minutes, late, cost)
    if child_goes:
        leg.child_arrive = depart + cond.minutes(child, opt.mode)
        leg.child_late = max(0, leg.child_arrive - cond.deadline(child))
        leg.cost += (cond.minutes(child, opt.mode) + LATE_WEIGHT * leg.child_late
                     + (CHILD_MISSED_PENALTY if leg.child_late > MISSED_LATENESS else 0))
    return leg


def enumerate_options(hh: Household, cond: Conditions, mid: str) -> list[Option]:
    """Individually feasible options for one agent, as shown by the journey planner."""
    m = hh.member(mid)
    opts: list[Option] = []
    no_car = cond.cars() == 0
    for mode in m.solo_modes():
        if cond.available(m, mode) and not (mode == Mode.CAR and no_car):
            opts.append(Option("", mid, mode))
    for cid, by_mode in hh.detour.get(mid, {}).items():
        child = hh.member(cid)
        for mode in ESCORT_MODES:
            if (mode in by_mode and (mode != Mode.CAR or (m.can_drive and not no_car))
                    and cond.available(m, mode) and cond.available(child, mode)):
                opts.append(Option("", mid, mode, cid))
    opts.append(Option("", mid, None))
    return [Option(f"O{i + 1}", o.member, o.mode, o.escort) for i, o in enumerate(opts)]


def describe(hh: Household, cond: Conditions, opt: Option) -> str:
    if opt.mode is None:
        return f"{opt.id}: do not travel today (stay at home)"
    leg = evaluate(hh, cond, opt)
    status = "on time" if leg.late == 0 else f"{leg.late} min LATE"
    s = f"{opt.id}: {opt.describe(hh)} - leave {clock(leg.depart)}, arrive {clock(leg.arrive)} ({status}), EUR {MONEY_EUR[opt.mode]:.1f}"
    if leg.child_arrive is not None:
        c = hh.member(opt.escort)
        s += f"; {c.name} arrives {clock(leg.child_arrive)}" + (f" ({leg.child_late} min late)" if leg.child_late else "")
    return s


def validate(hh: Household, cond: Conditions, plan: dict[str, Option]) -> list[dict[str, Any]]:
    """Joint-plan constraint check against what the household can know (observed view)."""
    v: list[dict[str, Any]] = []
    drivers = [mid for mid, o in plan.items() if o.mode == Mode.CAR]
    if len(drivers) > cond.cars():
        v.append({"type": "car_overclaim", "who": drivers, "cars": cond.cars()})
    for child in hh.children:
        if not cond.has_trip(child.id):
            continue
        escorts = [mid for mid, o in plan.items() if o.escort == child.id]
        if not escorts:
            v.append({"type": "escort_gap", "child": child.id})
        elif len(escorts) > 1:
            v.append({"type": "escort_duplicate", "child": child.id, "who": escorts})
    return v


@dataclass
class Outcome:
    member: str
    mode: str | None
    depart: int | None
    arrive: int | None
    late: int
    missed: bool
    cost: float
    escorted_by: str | None = None
    has_activity: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class Execution:
    outcomes: dict[str, Outcome]
    car_trips: list[dict[str, Any]]
    failures: Counter
    log: list[str]

    @property
    def household_cost(self) -> float:
        return round(sum(o.cost for o in self.outcomes.values()), 1)

    def summary(self) -> dict[str, Any]:
        acts = [o for o in self.outcomes.values() if o.has_activity]
        return {
            "activities": len(acts),
            "on_time": sum(1 for o in acts if not o.missed and o.late == 0),
            "late": sum(1 for o in acts if not o.missed and o.late > 0),
            "missed": sum(1 for o in acts if o.missed),
            "total_lateness": sum(o.late for o in acts if not o.missed),
            "household_cost": self.household_cost,
            "exec_car_unavailable": self.failures["car_unavailable"],
            "exec_child_unaccompanied": self.failures["child_unaccompanied"],
            "exec_duplicate_escort": self.failures["duplicate_escort"],
            "exec_wasted_trip": self.failures["wasted_trip"],
            "car_km_proxy": sum(t["minutes"] for t in self.car_trips),
        }


def _member_cost(cond: Conditions, m: Member, mode: Mode, minutes: int, late: int, missed: bool) -> float:
    return (minutes + cond.pref(m, mode) + MONEY_EUR[mode] * MIN_PER_EUR + LATE_WEIGHT * late
            + (MISSED_PENALTY if missed else 0))


def execute(hh: Household, plan: dict[str, Option], cond: Conditions) -> Execution:
    """Play the committed plans forward in departure order under `cond` (normally the truth).

    Physical constraints are enforced here: a car can only be taken from home if one is parked there
    and working. Nothing is silently repaired upstream; failures are recorded and the traveller
    re-plans on the spot with the best remaining mode (a declared behavioural assumption).
    """
    n_working = cond.cars()
    cars = [{"id": f"car{i + 1}", "at": "home", "working": i < n_working} for i in range(hh.n_cars)]
    outcomes: dict[str, Outcome] = {}
    car_trips: list[dict[str, Any]] = []
    failures: Counter = Counter()
    log: list[str] = []
    escorted: dict[str, tuple[str, Mode, int]] = {}

    def depart_of(o: Option) -> int:
        m = hh.member(o.member)
        if o.escort and cond.has_trip(o.escort):
            return max(m.ready, hh.member(o.escort).ready)
        return m.ready

    order = sorted(hh.agents, key=lambda a: (depart_of(plan[a.id]), hh.members.index(a)))
    for a in order:
        opt = plan[a.id]
        has_act = cond.has_trip(a.id)
        if opt.mode is None:
            outcomes[a.id] = Outcome(a.id, None, None, None, 0, has_act, MISSED_PENALTY if has_act else 0.0,
                                     has_activity=has_act, notes=["stayed home"])
            if has_act:
                log.append(f"{a.name} stayed home although their activity was on.")
            continue
        notes: list[str] = []
        depart, mode, escort = depart_of(opt), opt.mode, opt.escort
        extra = 0
        if escort and not cond.has_trip(escort):
            extra += hh.detour[a.id][escort][mode] + WASTED_ESCORT_EXTRA
            failures["wasted_trip"] += 1
            notes.append(f"went to {hh.member(escort).destination}, found it closed")
            log.append(f"{clock(depart)} {a.name} took {hh.member(escort).name} to a closed school and back.")
            escort = None
        elif escort and escort in escorted:
            failures["duplicate_escort"] += 1
            extra += DUPLICATE_ESCORT_DELAY
            notes.append(f"{hh.member(escort).name} had already left with {hh.member(escorted[escort][0]).name}")
            log.append(f"{clock(depart)} {a.name} planned to accompany {hh.member(escort).name}, who had already left.")
            escort = None
        car = None
        if mode == Mode.CAR:
            car = next((c for c in cars if c["at"] == "home" and c["working"]), None)
            if car is None:
                broken = any(c["at"] == "home" and not c["working"] for c in cars)
                failures["car_unavailable"] += 1
                extra += BROKEN_CAR_DELAY if broken else REPLAN_DELAY
                why = "the car would not start" if broken else "no car was left at home"
                away = [f"{c['id']} at {c['at']}" for c in cars if c["at"] != "home"]
                log.append(f"{clock(depart)} {a.name} wanted a car but {why}" + (f" ({', '.join(away)})." if away else "."))
                notes.append(why)
                mode = _replan(hh, cond, a, escort)
                if mode is None:
                    outcomes[a.id] = Outcome(a.id, None, depart, None, 0, has_act,
                                             MISSED_PENALTY if has_act else 0.0, has_activity=has_act,
                                             notes=notes + ["no alternative mode"])
                    continue
                if escort and mode not in hh.detour[a.id][escort]:
                    escort = None
            else:
                car["at"] = a.zone
        travel = cond.minutes(a, mode) + (hh.detour[a.id][escort][mode] if escort else 0)
        start = depart + extra
        arrive = start + travel
        if escort:
            escorted[escort] = (a.id, mode, start)
        if car is not None:
            car_trips.append({"car": car["id"], "driver": a.id, "passenger": escort, "from": "home",
                              "to": a.zone, "depart": start, "arrive": arrive, "minutes": travel})
        if not has_act:
            notes.append("activity cancelled; trip wasted")
            failures["wasted_trip"] += 1
        late = max(0, arrive - cond.deadline(a)) if has_act else 0
        missed = has_act and late > MISSED_LATENESS
        outcomes[a.id] = Outcome(a.id, mode.value, depart, arrive, late, missed,
                                 _member_cost(cond, a, mode, travel + extra, late, missed),
                                 has_activity=has_act, notes=notes)
    for child in hh.children:
        if not cond.has_trip(child.id):
            outcomes[child.id] = Outcome(child.id, None, None, None, 0, False, 0.0, has_activity=False,
                                         notes=["no school today"])
        elif child.id in escorted:
            adult, mode, t0 = escorted[child.id]
            arrive = t0 + cond.minutes(child, mode)
            late = max(0, arrive - cond.deadline(child))
            missed = late > MISSED_LATENESS
            outcomes[child.id] = Outcome(child.id, mode.value, t0, arrive, late, missed,
                                         cond.minutes(child, mode) + LATE_WEIGHT * late + (CHILD_MISSED_PENALTY if missed else 0),
                                         escorted_by=adult)
        else:
            failures["child_unaccompanied"] += 1
            log.append(f"Nobody accompanied {child.name}; {child.name} missed school.")
            outcomes[child.id] = Outcome(child.id, None, None, None, 0, True, CHILD_MISSED_PENALTY,
                                         notes=["nobody accompanied them"])
    return Execution(outcomes, car_trips, failures, log)


def _replan(hh: Household, cond: Conditions, a: Member, escort: str | None) -> Mode | None:
    """On-the-spot fallback after a failed car pick-up: cheapest remaining mode under `cond`."""
    candidates = [Option("", a.id, m, escort) for m in Mode
                  if m != Mode.CAR and cond.available(a, m) and (m != Mode.BIKE or a.can_bike)
                  and m in a.base and (escort is None or m in hh.detour[a.id][escort])]
    if not candidates and escort:
        return _replan(hh, cond, a, None)
    if not candidates:
        return None
    return min(candidates, key=lambda o: evaluate(hh, cond, o).cost).mode
