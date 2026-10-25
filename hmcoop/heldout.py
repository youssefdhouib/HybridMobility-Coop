"""Held-out test of the news interpreter on paraphrases written AFTER the single prompt revision and never
used for prompt development. Includes adversarial decoys that mention cars, schools or buses without changing
today's trips. The interpreter prompt was frozen before this file was first run.

    python3 -m hmcoop.heldout --model qwen2.5:3b
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .interpret import interpret
from .llm import OllamaClient
from .model import Effect, Event, Mode, clock
from .scenarios import HOUSEHOLDS, TARGETS

CAR = ["{car} failed its brake test yesterday; the garage says it is not safe to drive until the pads are replaced.",
       "{car} has a flat tyre this morning and the spare is flat too.",
       "Oil was leaking under {car} last night; the mechanic asked us to leave it parked until Thursday."]
ROAD = ["Traffic alert 07:00: roadworks have closed two lanes on the main road into {zone}; allow about 40 more minutes by car.",
        "Police have blocked the bridge towards {zone} after a crash; car journeys to {zone} will take around 40 minutes longer.",
        "Navigation app: severe congestion towards {zone} this morning, +40 min for drivers."]
CHILD_OFF = ["The teachers at the {dest} are on strike today; pupils should not come in.",
             "Message from the {dest}: because of a water leak, classes are cancelled today and {name} stays home.",
             "The {dest} is closed this morning for a gas inspection; no lessons today."]
ADULT_OFF = ["{name}'s boss: the {dest} is closed today for a building inspection, stay home.",
             "{name}'s shift at the {dest} has been cancelled today.",
             "The fire alarm system at the {dest} has failed; the building is closed today and {name} should not come."]
EARLY = ["{name}, the team meeting at the {dest} has been brought forward: please be there by {t}.",
         "Reminder for {name}: inspection visit today, you need to be at the {dest} half an hour earlier, at {t}.",
         "{name}'s manager asks everyone at the {dest} to start 30 minutes early today ({t})."]
DECOY = ["Car wash promotion: 20% off next week at the station on the ring road.",
         "The school canteen menu for next month is now online.",
         "Bus operator survey: tell us what you think of the new timetable (closes in two weeks).",
         "Weather: sunny and mild all week."]


def cases():
    for hid, hh in HOUSEHOLDS.items():
        t = TARGETS[hid]
        car = "the family car" if hh.n_cars == 1 else "the older of the two cars"
        off, early = hh.member(t["no_trip"]), hh.member(t["deadline"])
        for i, s in enumerate(CAR):
            yield hid, f"car_breakdown#{i}", Event("x", "", "unstructured", (lambda x: x[0].upper() + x[1:])(s.format(car=car)), [Effect("cars_down", amount=1)])
        for i, s in enumerate(ROAD):
            yield hid, f"ringroad#{i}", Event("x", "", "unstructured", s.format(zone=t["zone"]),
                                              [Effect("delay", mode=Mode.CAR, zone=t["zone"], amount=40)])
        for i, s in enumerate(CHILD_OFF if off.needs_escort else ADULT_OFF):
            yield hid, f"no_trip#{i}", Event("x", "", "unstructured", s.format(dest=off.destination, name=off.name),
                                             [Effect("no_trip", member=off.id)])
        for i, s in enumerate(EARLY):
            yield hid, f"deadline#{i}", Event("x", "", "unstructured",
                                              s.format(name=early.name, dest=early.destination, t=clock(early.deadline - 30)),
                                              [Effect("deadline", member=early.id, amount=-30)])
        for i, s in enumerate(DECOY):
            yield hid, f"decoy#{i}", Event("x", "", "decoy", s, [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    a = ap.parse_args()
    client = OllamaClient(model=a.model, cache_path="results/llm_cache.jsonl",
                          think=False if a.model.startswith("qwen3") else None)
    rows, by_type = [], {}
    for hid, case, ev in cases():
        effects, call, rec = interpret(client, HOUSEHOLDS[hid], ev)
        key = lambda e: (e.kind, e.mode, e.zone, e.member)  # noqa: E731
        exact = sorted(map(key, effects)) == sorted(map(key, ev.effects))
        amount_ok = exact and all(abs(g.amount - w.amount) <= 10 for g, w in zip(sorted(effects, key=key), sorted(ev.effects, key=key)))
        typ = case.split("#")[0]
        by_type.setdefault(typ, [0, 0, 0])
        by_type[typ][0] += exact
        by_type[typ][1] += amount_ok
        by_type[typ][2] += 1
        rows.append({"household": hid, "case": case, "text": ev.text, "exact": exact, "amount_ok": amount_ok,
                     "answer": rec, "latency_ms": round(call.latency_ms), "tokens": call.prompt_tokens + call.completion_tokens})
    n = len(rows)
    summary = {"model": a.model, "n": n, "exact": sum(r["exact"] for r in rows), "exact_and_amount": sum(r["amount_ok"] for r in rows),
               "by_type": {k: {"exact": f"{v[0]}/{v[2]}", "exact_and_amount": f"{v[1]}/{v[2]}"} for k, v in by_type.items()},
               "rows": rows}
    out = Path("results") / f"heldout_{a.model.replace(':', '_')}.json"
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    for r in rows:
        if not r["exact"]:
            print("MISS", r["household"], r["case"], "|", r["text"][:80], "->", r["answer"].get("effect"), r["answer"].get("member"), r["answer"].get("district"))


if __name__ == "__main__":
    main()
