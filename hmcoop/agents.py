"""Household-member agents with interchangeable decision engines.

  rule   : habit + generalized-cost heuristic over the planner's options (no text understanding).
  llm    : every decision and negotiation reply is produced by the local LLM, validated against
           the enumerated feasible options; invalid output -> labelled rule fallback.
  hybrid : starts in rule mode; escalates to the LLM for the whole episode when a gate fires
           (free-text news present, or the routine option is already late in the planner's view).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .llm import LLMCall, OllamaClient, choice_schema
from .model import Event, Household, Member, Message, Mode, Option, clock
from .world import Conditions, describe, enumerate_options, evaluate

SYSTEM = ("You simulate one person's morning travel decision in a research simulation of household "
          "mobility. Be realistic and practical: respect deadlines, your preferences and your family's "
          "needs, and take the morning news into account. The journey planner only knows official network "
          "information; free-text news may change the real situation and the planner does NOT account for it. "
          "Answer in JSON with a short reason (max 25 words) and the requested field.")


@dataclass
class Decision:
    agent: str
    stage: str
    option: str
    source: str          # rule | llm | fallback | protocol
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Agent:
    hh: Household
    me: Member
    obs: Conditions
    event: Event
    policy: str                       # rule | llm | hybrid
    client: OllamaClient | None
    calls: list[LLMCall] = field(default_factory=list)
    gate: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.options = enumerate_options(self.hh, self.obs, self.me.id)
        self.by_id = {o.id: o for o in self.options}
        if self.policy == "hybrid":
            if self.event.is_text_only:
                self.gate.append("free-text news outside the rule vocabulary")
            if evaluate(self.hh, self.obs, self.rule_choice()).late > 0:
                self.gate.append("routine option already late in planner view")
        self.engine = "llm" if self.policy == "llm" or (self.policy == "hybrid" and self.gate) else "rule"

    # ---------- deterministic machinery ----------
    def cost(self, o: Option) -> float:
        return evaluate(self.hh, self.obs, o).cost

    def best(self, opts: list[Option]) -> Option:
        return min(opts, key=lambda o: (self.cost(o), o.id))

    def rule_choice(self, allowed: list[Option] | None = None) -> Option:
        if not self.obs.has_trip(self.me.id):  # activity known to be cancelled: stay home
            return next(o for o in (allowed or self.options) if o.mode is None)
        opts = [o for o in (allowed or self.options) if o.mode is not None]
        if allowed is None:
            routine = [c for c, a in self.hh.routine_escort.items() if a == self.me.id and self.obs.has_trip(c)]
            if routine:
                habitual = [o for o in opts if o.escort in routine]
            else:
                habitual = [o for o in opts if o.escort is None]
            opts = habitual or opts
        return self.best(opts)

    def concession_cost(self, current: Option) -> tuple[float, Option | None]:
        """Extra cost (planner view) of giving up the car, and the best non-car replacement."""
        alts = [o for o in self.options if o.mode not in (Mode.CAR, None) and o.escort == current.escort] \
            or [o for o in self.options if o.mode not in (Mode.CAR, None)]
        if not alts:
            return float("inf"), None
        alt = self.best(alts)
        return self.cost(alt) - self.cost(current), alt

    def escort_extra(self, child: str, current: Option) -> tuple[float, Option | None]:
        opts = [o for o in self.options if o.escort == child]
        if not opts:
            return float("inf"), None
        o = self.best(opts)
        return self.cost(o) - self.cost(current), o

    # ---------- prompt helpers ----------
    def _persona(self, comm: bool) -> str:
        m, hh, obs = self.me, self.hh, self.obs
        likes = [k.value for k, v in m.prefs.items() if v < 0]
        dislikes = [k.value for k, v in m.prefs.items() if v > 0]
        lines = [f"You are {m.name}, {m.age}, {m.role}. This morning you travel from home to the {m.destination} "
                 f"(district {m.zone}). You can leave from {clock(m.ready)}; you must arrive by {clock(m.deadline)}.",
                 f"Habit: you {m.habit}." if m.habit else ""]
        if likes or dislikes:
            lines.append("Preferences: " + "; ".join([f"you like the {x}" for x in likes] +
                                                    [f"you dislike the {x}" for x in dislikes]) + ".")
        drivers = [x.name for x in hh.agents if x.can_drive]
        lines.append(f"Household: {', '.join(x.name for x in hh.members)}. It owns {hh.n_cars} car(s); "
                     f"drivers: {', '.join(drivers) or 'nobody'}.")
        for c in hh.children:
            usual = hh.member(hh.routine_escort[c.id]).name if c.id in hh.routine_escort else "someone"
            lines.append(f"{c.name} ({c.age}) cannot travel alone and must be accompanied to the {c.destination} "
                         f"(district {c.zone}) by {clock(c.deadline)}; usually {usual} does it.")
        lines.append("Morning news:\n- " + self.event.text if self.event.text else "Morning news: nothing special.")
        if not comm:
            lines.append("You cannot contact the other household members this morning; decide on your own.")
        return "\n".join(x for x in lines if x)

    def _opts_text(self, opts: list[Option]) -> str:
        return "\n".join(describe(self.hh, self.obs, o) for o in opts)

    def _ask(self, purpose: str, user: str, field_name: str, allowed: list[str],
             extra: dict[str, Any] | None = None) -> LLMCall:
        assert self.client is not None
        call = self.client.chat(purpose, self.me.id, SYSTEM, user, choice_schema(field_name, allowed, extra))
        self.calls.append(call)
        return call

    # ---------- decisions ----------
    def decide(self, inbox: list[Message], comm: bool, stage: str = "initial",
               allowed: list[Option] | None = None, note: str = "") -> tuple[Option, Decision]:
        if self.engine == "rule":
            o = self.rule_choice(allowed)
            return o, Decision(self.me.id, stage, o.id, "rule", f"lowest generalized cost under habit ({self.cost(o):.0f})")
        opts = allowed or self.options
        msgs = [f"- {x.sender} -> {x.receiver} [{x.performative}]: {x.text}" for x in inbox
                if x.sender not in (self.me.id, "environment")]
        user = (self._persona(comm) + ("\nHousehold messages:\n" + "\n".join(msgs) if msgs else "")
                + (f"\n{note}" if note else "")
                + "\nYour options (planner estimates):\n" + self._opts_text(opts)
                + "\nChoose exactly one option ID.")
        call = self._ask(f"decide:{stage}", user, "option", [o.id for o in opts])
        if call.ok and call.data and call.data["option"] in {o.id for o in opts}:
            o = self.by_id[call.data["option"]]
            return o, Decision(self.me.id, stage, o.id, "llm", str(call.data.get("reason", ""))[:240])
        o = self.rule_choice(allowed)
        return o, Decision(self.me.id, stage, o.id, "fallback", f"LLM failed ({call.error}); rule used")

    def car_reply(self, current: Option, claims: dict[str, float], excess: int, rnd: int,
                  inbox: list[Message]) -> tuple[str, Option, Decision]:
        """keep or concede the car. `claims`: claimant -> declared concession cost."""
        my_cost, alt = self.concession_cost(current)
        rule_concede = alt is not None and \
            sorted(claims, key=lambda k: (claims[k], k)).index(self.me.id) < excess
        if self.engine == "rule" or alt is None:
            act = "concede" if rule_concede else "keep"
            o = alt if rule_concede else current
            return act, o, Decision(self.me.id, f"car_round{rnd}", o.id, "rule",
                                    f"{act}: my concession cost {my_cost:.0f} vs others")
        non_car = [o for o in self.options if o.mode not in (Mode.CAR, None)]
        others = "\n".join(f"- {self.hh.member(k).name}: giving up the car costs them about {v:.0f} min-equivalent"
                           for k, v in claims.items() if k != self.me.id)
        msgs = [f"- {x.sender} [{x.performative}]: {x.text}" for x in inbox[-8:] if x.sender != self.me.id]
        user = (self._persona(True) + f"\nCONFLICT (round {rnd}): only {self.obs.cars()} car(s) but "
                f"{len(claims)} people plan to drive. You plan: {current.describe(self.hh)}. "
                f"Giving up the car costs you about {my_cost:.0f} min-equivalent.\nOthers:\n{others}"
                + ("\nRecent messages:\n" + "\n".join(msgs) if msgs else "")
                + "\nYour options without the car:\n" + self._opts_text(non_car)
                + "\nDecide: action 'keep' (you keep the car, option 'none') or 'concede' (pick a non-car option).")
        call = self._ask(f"car_round{rnd}", user, "option", [o.id for o in non_car] + ["none"],
                         {"action": {"type": "string", "enum": ["keep", "concede"]}})
        d = call.data or {}
        if call.ok and d.get("action") == "keep":
            return "keep", current, Decision(self.me.id, f"car_round{rnd}", current.id, "llm", str(d.get("reason", ""))[:240])
        if call.ok and d.get("action") == "concede" and d.get("option") in {o.id for o in non_car}:
            o = self.by_id[d["option"]]
            return "concede", o, Decision(self.me.id, f"car_round{rnd}", o.id, "llm", str(d.get("reason", ""))[:240])
        act = "concede" if rule_concede else "keep"
        o = alt if rule_concede else current
        err = call.error or f"inconsistent reply {d}"
        return act, o, Decision(self.me.id, f"car_round{rnd}", o.id, "fallback", f"LLM failed ({err}); rule used")

    def escort_reply(self, child: Member, current: Option, extras: dict[str, float], rnd: int,
                     inbox: list[Message]) -> tuple[str, Option, Decision]:
        my_extra, best = self.escort_extra(child.id, current)
        rule_accept = best is not None and min(extras, key=lambda k: (extras[k], k)) == self.me.id
        if self.engine == "rule" or best is None:
            act = "accept" if rule_accept else "decline"
            o = best if rule_accept else current
            return act, o, Decision(self.me.id, f"escort_round{rnd}", o.id, "rule",
                                    f"{act}: my extra cost {my_extra:.0f} vs others")
        mine = [o for o in self.options if o.escort == child.id]
        others = "\n".join(f"- {self.hh.member(k).name}: accompanying costs them about {v:.0f} min-equivalent extra"
                           for k, v in extras.items() if k != self.me.id)
        user = (self._persona(True) + f"\nREQUEST (round {rnd}): {child.name} has nobody to accompany them to the "
                f"{child.destination} by {clock(self.obs.deadline(child))}. You plan: {current.describe(self.hh)}. "
                f"Accompanying costs you about {my_extra:.0f} min-equivalent extra.\nOther possible companions:\n{others or '- none'}"
                + "\nYour options that include accompanying them:\n" + self._opts_text(mine)
                + "\nDecide: action 'accept' (pick one of these options) or 'decline' (option 'none').")
        call = self._ask(f"escort_round{rnd}", user, "option", [o.id for o in mine] + ["none"],
                         {"action": {"type": "string", "enum": ["accept", "decline"]}})
        d = call.data or {}
        if call.ok and d.get("action") == "decline":
            return "decline", current, Decision(self.me.id, f"escort_round{rnd}", current.id, "llm", str(d.get("reason", ""))[:240])
        if call.ok and d.get("action") == "accept" and d.get("option") in {o.id for o in mine}:
            o = self.by_id[d["option"]]
            return "accept", o, Decision(self.me.id, f"escort_round{rnd}", o.id, "llm", str(d.get("reason", ""))[:240])
        act = "accept" if rule_accept else "decline"
        o = best if rule_accept else current
        err = call.error or f"inconsistent reply {d}"
        return act, o, Decision(self.me.id, f"escort_round{rnd}", o.id, "fallback", f"LLM failed ({err}); rule used")
