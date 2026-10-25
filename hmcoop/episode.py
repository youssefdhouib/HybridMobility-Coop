"""One simulated morning: decide -> (negotiate) -> commit -> execute under ground truth -> measure.

Communication OFF: every agent plans alone; incompatible intentions are only discovered at execution.
Communication ON : decision-time protocol over a household channel with performatives
                   inform / request / propose / counter / accept / reject / commit.
Centralised baselines (no agents, no messages) are in `central_plan`.
"""
from __future__ import annotations

import itertools
import time
from typing import Any

from .agents import Agent, Decision
from .interpret import interpret, matches_truth
from .llm import OllamaClient
from .model import Event, Household, Message, Mode, Option, clock
from .scenarios import make_scenario
from .world import Conditions, enumerate_options, evaluate, execute, validate

POLICIES = ("rule", "llm", "hybrid", "interp")
CENTRAL = ("central", "oracle")
MAX_CAR_ROUNDS = 3
MAX_ESCORT_ROUNDS = 2
MAX_RESOLUTION_PASSES = 4


class Episode:
    def __init__(self, hh: Household, event: Event, policy: str, comm: bool, client: OllamaClient | None):
        self.hh, self.event, self.policy, self.comm = hh, event, policy, comm
        self.obs, self.truth = Conditions.observed(hh, event), Conditions.truth(hh, event)
        self.extra_calls: list = []
        self.interpretation: dict[str, Any] | None = None
        if policy == "interp" and event.is_text_only:
            # LLM reads the news once for the household; rules + protocol then decide on the updated view.
            effects, call, rec = interpret(client, hh, event)
            self.extra_calls.append(call)
            rec["correct"] = matches_truth(event, effects)
            self.interpretation = rec
            self.obs = Conditions(hh, self.obs.effects + effects, "observed+interpreted")
        self.agents = {m.id: Agent(hh, m, self.obs, event, policy, client) for m in hh.agents}
        self.plan: dict[str, Option] = {}
        self.msgs: list[Message] = []
        self.decisions: list[Decision] = []
        self.rnd = 0
        self.stats = {"car_negotiations": 0, "escort_negotiations": 0, "duplicate_resolutions": 0,
                      "negotiation_rounds": 0, "deadlocks": 0, "protocol_fallbacks": 0}

    def say(self, sender: str, receiver: str, perf: str, content: dict[str, Any], text: str, source: str) -> None:
        self.msgs.append(Message(self.rnd, sender, receiver, perf, content, text, source))

    def _set(self, aid: str, o: Option, d: Decision) -> None:
        self.plan[aid] = o
        self.decisions.append(d)

    def _plan_text(self, o: Option) -> str:
        if o.mode is None:
            return "I will not travel today."
        leg = evaluate(self.hh, self.obs, o)
        return f"I plan: {o.describe(self.hh)}, leaving {clock(leg.depart)}, arriving {clock(leg.arrive)}."

    # ------------------------------------------------------------------
    def run(self) -> dict[str, Any]:
        t0 = time.perf_counter()
        if self.event.text:
            self.say("environment", "all", "inform", {"event": self.event.id}, self.event.text, "environment")
        if self.comm:
            for c in self.hh.children:
                if self.obs.has_trip(c.id):
                    self.say(c.id, "all", "request", {"need": "escort", "deadline": clock(c.deadline)},
                             f"Who takes me to the {c.destination}? I must be there by {clock(c.deadline)}.", "protocol")
        inbox = list(self.msgs)  # simultaneous initial proposals: nobody sees the others' plans yet
        for aid, ag in self.agents.items():
            o, d = ag.decide(inbox, self.comm)
            self._set(aid, o, d)
            if self.comm:
                self.say(aid, "all", "propose", {"option": o.id, "mode": o.mode.value if o.mode else None,
                                                 "escort": o.escort}, d.reason if d.source == "llm" else self._plan_text(o),
                         d.source)
        initial_violations = validate(self.hh, self.obs, self.plan)
        if self.comm:
            self._resolve()
            for aid, o in self.plan.items():
                self.say(aid, "all", "commit", {"option": o.id}, self._plan_text(o), "protocol")
        committed_violations = validate(self.hh, self.obs, self.plan)
        ex = execute(self.hh, self.plan, self.truth)
        return self._result(initial_violations, committed_violations, ex, (time.perf_counter() - t0) * 1000)

    # ------------------------------------------------------------------
    def _resolve(self) -> None:
        for _ in range(MAX_RESOLUTION_PASSES):
            viol = validate(self.hh, self.obs, self.plan)
            if not viol:
                return
            v = viol[0]
            self.rnd += 1
            if v["type"] == "car_overclaim":
                self._negotiate_car(v["who"], v["cars"])
            elif v["type"] == "escort_gap":
                self._negotiate_escort(v["child"])
            else:
                self._resolve_duplicate(v["child"], v["who"])

    def _negotiate_car(self, claimants: list[str], cars: int) -> None:
        self.stats["car_negotiations"] += 1
        for rnd in range(1, MAX_CAR_ROUNDS + 1):
            self.stats["negotiation_rounds"] += 1
            claims = {a: self.agents[a].concession_cost(self.plan[a])[0] for a in claimants}
            for a in claimants:
                self.say(a, "all", "counter", {"resource": "car", "concession_cost": round(claims[a], 1)},
                         f"I need the car: without it my morning costs ~{claims[a]:.0f} min-equivalent more.", "protocol")
            excess = len(claimants) - cars
            keepers = []
            for a in claimants:
                act, o, d = self.agents[a].car_reply(self.plan[a], claims, excess, rnd, self.msgs)
                self._set(a, o, d)
                if act == "keep":
                    keepers.append(a)
                    self.say(a, "all", "reject", {"resource": "car", "action": "keep"},
                             d.reason if d.source == "llm" else "I keep my claim on the car.", d.source)
                else:
                    self.say(a, "all", "accept", {"resource": "car", "action": "concede", "option": o.id},
                             d.reason if d.source == "llm" else f"I give up the car. {self._plan_text(o)}", d.source)
            claimants = keepers
            if len(claimants) <= cars:
                return
        # Deadlock: explicit, logged tie-break by the protocol (lowest concession cost gives way).
        self.stats["deadlocks"] += 1
        claims = {a: self.agents[a].concession_cost(self.plan[a]) for a in claimants}
        for a in sorted(claimants, key=lambda k: (claims[k][0], k))[:len(claimants) - cars]:
            alt = claims[a][1]
            if alt is not None:
                self.stats["protocol_fallbacks"] += 1
                self._set(a, alt, Decision(a, "car_deadlock", alt.id, "protocol", "deadlock tie-break: lowest concession cost"))
                self.say("protocol", a, "reject", {"resource": "car"}, "Deadlock: tie-break assigns you a non-car option.", "protocol")

    def _negotiate_escort(self, child_id: str) -> None:
        self.stats["escort_negotiations"] += 1
        child = self.hh.member(child_id)
        cands = [a for a in self.agents if self.agents[a].escort_extra(child_id, self.plan[a])[1] is not None]
        if not cands:
            return
        for rnd in range(1, MAX_ESCORT_ROUNDS + 1):
            self.stats["negotiation_rounds"] += 1
            extras = {a: self.agents[a].escort_extra(child_id, self.plan[a])[0] for a in cands}
            for a in cands:
                self.say(child_id, a, "request", {"need": "escort", "round": rnd},
                         f"Can you take me to the {child.destination}?", "protocol")
            accepted: list[tuple[float, str, Option]] = []
            for a in cands:
                act, o, d = self.agents[a].escort_reply(child, self.plan[a], extras, rnd, self.msgs)
                self.decisions.append(d)
                if act == "accept":
                    accepted.append((extras[a], a, o))
                    self.say(a, child_id, "propose", {"option": o.id},
                             d.reason if d.source == "llm" else f"I can take you. {self._plan_text(o)}", d.source)
                else:
                    self.say(a, child_id, "reject", {"need": "escort"},
                             d.reason if d.source == "llm" else "I cannot take you this morning.", d.source)
            if accepted:
                _, a, o = min(accepted, key=lambda t: (t[0], t[1]))
                self.plan[a] = o
                self.say(child_id, a, "accept", {"option": o.id}, f"Thanks, I go with {self.hh.member(a).name}.", "protocol")
                for _, other, _ in accepted:
                    if other != a:
                        self.say(child_id, other, "reject", {}, "Thanks, someone else is taking me.", "protocol")
                return
        self.stats["deadlocks"] += 1
        extras2 = {a: self.agents[a].escort_extra(child_id, self.plan[a]) for a in cands}
        a = min(cands, key=lambda k: (extras2[k][0], k))
        self.stats["protocol_fallbacks"] += 1
        self._set(a, extras2[a][1], Decision(a, "escort_deadlock", extras2[a][1].id, "protocol",
                                             "deadlock tie-break: lowest extra cost accompanies"))
        self.say("protocol", a, "commit", {"escort": child_id}, "Deadlock: tie-break assigns you as companion.", "protocol")

    def _resolve_duplicate(self, child_id: str, who: list[str]) -> None:
        self.stats["duplicate_resolutions"] += 1
        self.stats["negotiation_rounds"] += 1

        def keep_cost(a: str) -> float:  # how much this escort would save by dropping the child
            ag = self.agents[a]
            solo = [o for o in ag.options if o.escort != child_id and o.mode is not None]
            return ag.cost(self.plan[a]) - ag.cost(ag.best(solo)) if solo else 0.0
        keep = min(who, key=lambda a: (keep_cost(a), a))
        self.say(child_id, keep, "accept", {"escort": keep}, f"I go with {self.hh.member(keep).name}.", "protocol")
        for a in who:
            if a == keep:
                continue
            self.say(child_id, a, "reject", {"escort": a},
                     f"{self.hh.member(keep).name} is already taking me, thanks.", "protocol")
            ag = self.agents[a]
            allowed = [o for o in ag.options if o.escort != child_id]
            o, d = ag.decide(self.msgs, True, stage="replan", allowed=allowed,
                             note=f"{self.hh.member(child_id).name} will go with {self.hh.member(keep).name}; "
                                  "choose a new plan for yourself.")
            self._set(a, o, d)
            self.say(a, "all", "propose", {"option": o.id}, d.reason if d.source == "llm" else self._plan_text(o), d.source)

    # ------------------------------------------------------------------
    def _result(self, initial: list, committed: list, ex, elapsed_ms: float) -> dict[str, Any]:
        calls = self.extra_calls + [c for ag in self.agents.values() for c in ag.calls]
        llm_decisions = sum(d.source == "llm" for d in self.decisions)
        return {
            "household": self.hh.id, "event": self.event.id, "event_kind": self.event.kind,
            "policy": self.policy, "comm": self.comm,
            "metrics": {
                **ex.summary(),
                "intent_conflicts_initial": len(initial),
                "violations_committed": len(committed),
                "messages": len(self.msgs),
                **self.stats,
                "llm_calls": len(calls),
                "llm_invalid": sum(not c.ok for c in calls),
                "fallback_decisions": sum(d.source == "fallback" for d in self.decisions),
                "llm_decisions": llm_decisions,
                "rule_decisions": sum(d.source == "rule" for d in self.decisions),
                "prompt_tokens": sum(c.prompt_tokens for c in calls),
                "completion_tokens": sum(c.completion_tokens for c in calls),
                "llm_latency_ms": round(sum(c.latency_ms for c in calls), 1),
                "llm_cached_calls": sum(c.cached for c in calls),
                "escalated_agents": sum(ag.engine == "llm" for ag in self.agents.values()) if self.policy == "hybrid" else None,
                "wall_ms": round(elapsed_ms, 1),
            },
            "gate": {a: ag.gate for a, ag in self.agents.items()},
            "interpretation": self.interpretation,
            "plan": {a: {"option": o.id, "mode": o.mode.value if o.mode else None, "escort": o.escort,
                         "label": o.describe(self.hh)} for a, o in self.plan.items()},
            "initial_violations": initial, "committed_violations": committed,
            "decisions": [d.as_dict() for d in self.decisions],
            "messages": [m.as_dict() for m in self.msgs],
            "llm_calls": [c.as_dict() for c in calls],
            "execution": {"outcomes": {k: v.__dict__ for k, v in ex.outcomes.items()},
                          "car_trips": ex.car_trips, "log": ex.log},
        }


def central_plan(hh: Household, cond: Conditions) -> dict[str, Option]:
    """Exhaustive joint search minimising simulated household cost under `cond`.
    With cond=observed this is an equal-information deterministic coordinator; with cond=truth it is
    an oracle upper bound that no agent could reach (it reads ground truth)."""
    per_agent = [enumerate_options(hh, cond, a.id) for a in hh.agents]
    best, best_cost = None, float("inf")
    for combo in itertools.product(*per_agent):
        plan = {o.member: o for o in combo}
        c = execute(hh, plan, cond).household_cost
        if c < best_cost:
            best, best_cost = plan, c
    assert best is not None
    return best


def run_central(hh: Household, event: Event, which: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    obs, truth = Conditions.observed(hh, event), Conditions.truth(hh, event)
    plan = central_plan(hh, obs if which == "central" else truth)
    ex = execute(hh, plan, truth)
    viol = validate(hh, obs, plan)
    return {
        "household": hh.id, "event": event.id, "event_kind": event.kind, "policy": which, "comm": None,
        "metrics": {**ex.summary(), "intent_conflicts_initial": len(viol), "violations_committed": len(viol),
                    "messages": 0, "llm_calls": 0, "llm_invalid": 0, "fallback_decisions": 0,
                    "prompt_tokens": 0, "completion_tokens": 0, "llm_latency_ms": 0.0,
                    "wall_ms": round((time.perf_counter() - t0) * 1000, 1)},
        "plan": {a: {"option": o.id, "mode": o.mode.value if o.mode else None, "escort": o.escort,
                     "label": o.describe(hh)} for a, o in plan.items()},
        "decisions": [], "messages": [], "llm_calls": [], "gate": {},
        "initial_violations": viol, "committed_violations": viol,
        "execution": {"outcomes": {k: v.__dict__ for k, v in ex.outcomes.items()},
                      "car_trips": ex.car_trips, "log": ex.log},
    }


def run_episode(household: str, event: str, policy: str, comm: bool | None, seed: int = 0,
                client: OllamaClient | None = None) -> dict[str, Any]:
    hh, ev = make_scenario(household, event, seed)
    if policy in CENTRAL:
        res = run_central(hh, ev, policy)
    else:
        if policy in ("llm", "hybrid", "interp") and client is None:
            raise ValueError("LLM and hybrid policies need an OllamaClient; refusing to fake model output")
        res = Episode(hh, ev, policy, bool(comm), client).run()
    res["seed"] = seed
    res["event_text"] = ev.text
    res["oracle_cost"] = execute(hh, central_plan(hh, Conditions.truth(hh, ev)), Conditions.truth(hh, ev)).household_cost
    res["metrics"]["regret"] = round(res["metrics"]["household_cost"] - res["oracle_cost"], 1)
    return res
