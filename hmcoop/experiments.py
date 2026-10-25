"""Factorial experiment runner (resumable) and analysis.

    python3 -m hmcoop.experiments run --seeds 0 1 2
    python3 -m hmcoop.experiments analyze
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .episode import run_episode
from .llm import OllamaClient
from .scenarios import EVENTS, HOUSEHOLDS

CONDITIONS = [("rule", False), ("rule", True), ("llm", False), ("llm", True), ("hybrid", False), ("hybrid", True),
              ("interp", False), ("interp", True), ("central", None), ("oracle", None)]
ORDER = ["rule-off", "rule-on", "llm-off", "llm-on", "hybrid-off", "hybrid-on", "interp-off", "interp-on",
         "central", "oracle"]
LLM_POLICIES = ("llm", "hybrid", "interp")


def label(policy: str, comm: bool | None) -> str:
    return policy if comm is None else f"{policy}-{'on' if comm else 'off'}"


def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["household"], r["event"], r["seed"], r["condition"], r.get("model")))
    client = OllamaClient(model=args.model, cache_path=args.cache, temperature=args.temperature,
                          think=False if args.model.startswith("qwen3") else None)
    ok, why = client.available()
    needs_llm = any(p in LLM_POLICIES for p, _ in CONDITIONS if p in args.policies)
    if needs_llm and not ok:
        sys.exit(f"Refusing to run LLM conditions: {why}")
    meta = {"model": args.model, "client": client.config(), "python": platform.python_version(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    meta_file = out.parent / f"run_meta_{args.model.replace(':', '_')}.json"
    meta_file.write_text(json.dumps(meta, indent=2))
    grid = [(h, e, s) for s in args.seeds for h in args.households for e in args.events]
    t0 = time.time()
    with out.open("a") as f:
        for i, (h, e, s) in enumerate(grid):
            for p, c in CONDITIONS:
                if p not in args.policies:
                    continue
                cond = label(p, c)
                model = args.model if p in LLM_POLICIES else None
                if (h, e, s, cond, model) in done:
                    continue
                r = run_episode(h, e, p, c, s, client if p in LLM_POLICIES else None)
                r.update(condition=cond, model=model)
                f.write(json.dumps(r) + "\n")
                f.flush()
            el = time.time() - t0
            print(f"[{i + 1}/{len(grid)}] {h}/{e}/seed{s} done  ({el / 60:.1f} min elapsed)", flush=True)


# ----------------------------------------------------------------------------- analysis
def _boot(xs: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if len(xs) < 2:
        return (xs[0], xs[0]) if xs else (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    runs = [json.loads(l) for l in Path(args.out).read_text().splitlines()]
    if args.model_filter:
        runs = [r for r in runs if r.get("model") in (None, args.model_filter)]
    if args.seed_filter is not None:
        runs = [r for r in runs if r["seed"] in args.seed_filter]
    by: dict[str, dict[tuple, dict]] = defaultdict(dict)
    for r in runs:
        by[r["condition"]][(r["household"], r["event"], r["seed"])] = r
    keys = sorted(set.intersection(*(set(v) for v in by.values())))  # only complete instances: paired design
    conds = [c for c in ORDER if c in by]
    M = lambda c, k, m: by[c][k]["metrics"].get(m) or 0  # noqa: E731

    table = {}
    for c in conds:
        regs = [M(c, k, "regret") for k in keys]
        acts = sum(M(c, k, "activities") for k in keys)
        lo, hi = _boot(regs)
        table[c] = {
            "n": len(keys),
            "regret_mean": round(st.fmean(regs), 1), "regret_ci95": [round(lo, 1), round(hi, 1)],
            "on_time_rate": round(sum(M(c, k, "on_time") for k in keys) / acts, 3),
            "missed_rate": round(sum(M(c, k, "missed") for k in keys) / acts, 3),
            "lateness_min_mean": round(st.fmean(M(c, k, "total_lateness") for k in keys), 1),
            "intent_conflicts_initial": round(st.fmean(M(c, k, "intent_conflicts_initial") for k in keys), 2),
            "violations_committed": round(st.fmean(M(c, k, "violations_committed") for k in keys), 2),
            "exec_failures": round(st.fmean(M(c, k, "exec_car_unavailable") + M(c, k, "exec_child_unaccompanied")
                                            + M(c, k, "exec_duplicate_escort") + M(c, k, "exec_wasted_trip")
                                            for k in keys), 2),
            "messages": round(st.fmean(M(c, k, "messages") for k in keys), 1),
            "deadlocks": sum(M(c, k, "deadlocks") for k in keys),
            "llm_calls_mean": round(st.fmean(M(c, k, "llm_calls") for k in keys), 2),
            "llm_invalid": sum(M(c, k, "llm_invalid") for k in keys),
            "fallback_decisions": sum(M(c, k, "fallback_decisions") for k in keys),
            "tokens_mean": round(st.fmean(M(c, k, "prompt_tokens") + M(c, k, "completion_tokens") for k in keys)),
            "llm_latency_s_mean": round(st.fmean(M(c, k, "llm_latency_ms") for k in keys) / 1000, 2),
        }

    kinds = ["none", "structured", "unstructured", "decoy"]
    by_kind = {c: {kd: round(st.fmean([M(c, k, "regret") for k in keys if by[c][k]["event_kind"] == kd] or [0]), 1)
                   for kd in kinds} for c in conds}
    by_event = {c: {e: round(st.fmean([M(c, k, "regret") for k in keys if k[1] == e] or [0]), 1) for e in EVENTS}
                for c in conds}

    pairs = [("rule-on", "rule-off"), ("llm-on", "llm-off"), ("hybrid-on", "hybrid-off"), ("llm-on", "rule-on"),
             ("hybrid-on", "rule-on"), ("hybrid-on", "llm-on"), ("hybrid-off", "rule-off"), ("interp-on", "rule-on"),
             ("interp-on", "hybrid-on"), ("interp-off", "rule-off"), ("rule-on", "central"), ("llm-on", "central"),
             ("interp-on", "central")]
    paired = {}
    for a, b in pairs:
        if a in by and b in by:
            d = [M(a, k, "regret") - M(b, k, "regret") for k in keys]
            lo, hi = _boot(d, seed=1)
            paired[f"{a} vs {b}"] = {"mean_diff": round(st.fmean(d), 1), "ci95": [round(lo, 1), round(hi, 1)],
                                     "better": sum(x < -1e-9 for x in d), "tie": sum(abs(x) <= 1e-9 for x in d),
                                     "worse": sum(x > 1e-9 for x in d)}
        for kd in ("unstructured",):
            if a in by and b in by:
                d = [M(a, k, "regret") - M(b, k, "regret") for k in keys if by[a][k]["event_kind"] == kd]
                if d:
                    lo, hi = _boot(d, seed=2)
                    paired[f"{a} vs {b}"]["unstructured_only"] = {"mean_diff": round(st.fmean(d), 1),
                                                                  "ci95": [round(lo, 1), round(hi, 1)], "n": len(d)}

    # Negative control: does irrelevant text change plans? Compare decoy vs ordinary day, same household/seed.
    overreact = {}
    for c in conds:
        changed, total, dcost = 0, 0, []
        for (h, e, s) in keys:
            if e != "decoy" or (h, "none", s) not in by[c]:
                continue
            p1, p0 = by[c][(h, e, s)]["plan"], by[c][(h, "none", s)]["plan"]
            changed += sum(p1[a]["label"] != p0[a]["label"] for a in p1)
            total += len(p1)
            dcost.append(by[c][(h, e, s)]["metrics"]["household_cost"] - by[c][(h, "none", s)]["metrics"]["household_cost"])
        if total:
            overreact[c] = {"agents_changed_plan": f"{changed}/{total}", "mean_cost_delta": round(st.fmean(dcost), 1)}

    # Hybrid escalation and savings
    esc = {}
    for c in ("hybrid-off", "hybrid-on"):
        if c in by and c.replace("hybrid", "llm") in by:
            ll = c.replace("hybrid", "llm")
            esc[c] = {
                "episodes_with_escalation": sum(1 for k in keys if (M(c, k, "escalated_agents") or 0) > 0),
                "episodes": len(keys),
                "llm_calls_total": sum(M(c, k, "llm_calls") for k in keys),
                f"{ll}_calls_total": sum(M(ll, k, "llm_calls") for k in keys),
                "escalations_on_ordinary_or_structured_days": sum(
                    1 for k in keys if (M(c, k, "escalated_agents") or 0) > 0 and by[c][k]["event_kind"] in ("none", "structured")),
            }
    model = args.model_filter or "qwen2.5:3b"
    uptake = {c: _uptake([by[c][k] for k in keys]) for c in conds}
    interp_acc = {}
    for c in ("interp-off", "interp-on"):
        if c in by:
            recs = [by[c][k] for k in keys if by[c][k].get("interpretation")]
            per: dict[str, list[bool]] = defaultdict(list)
            for r in recs:
                per[r["event"]].append(bool(r["interpretation"]["correct"]))
            interp_acc[c] = {e: f"{sum(v)}/{len(v)}" for e, v in sorted(per.items())}
    meta_path = Path(args.out).parent / f"run_meta_{model.replace(':', '_')}.json"
    summary = {"instances": len(keys), "conditions": conds, "table": table, "regret_by_event_kind": by_kind,
               "regret_by_event": by_event, "paired": paired, "decoy_overreaction": overreact, "hybrid": esc,
               "uptake": uptake, "interpretation_accuracy": interp_acc,
               "run_meta": json.loads(meta_path.read_text()) if meta_path.exists() else {}}
    outdir = Path(args.out).parent
    tag = ("" if model == "qwen2.5:3b" else "_" + model.replace(":", "_")) + \
        ("" if args.seed_filter is None else "_seed" + "-".join(map(str, args.seed_filter)))
    (outdir / f"summary{tag}.json").write_text(json.dumps(summary, indent=2))
    (outdir / f"summary{tag}.md").write_text(_markdown(summary))
    _figures(summary, outdir / f"figures{tag}")
    print((outdir / f"summary{tag}.md").read_text())
    return summary


def _uptake(rs: list[dict[str, Any]]) -> dict[str, str]:
    """Is the committed plan consistent with the text-only news? (behavioural check, per event)"""
    from .scenarios import TARGETS, make_scenario
    from .world import Conditions
    res: dict[str, list[bool]] = defaultdict(list)
    for r in rs:
        e, h = r["event"], r["household"]
        plan = r["plan"]
        if e == "car_breakdown":
            hh, ev = make_scenario(h, e, r["seed"])
            res[e].append(sum(p["mode"] == "car" for p in plan.values()) <= Conditions.truth(hh, ev).cars())
        elif e == "ringroad_accident":
            z = TARGETS[h]["zone"]
            hh, _ = make_scenario(h, e, r["seed"])
            res[e].append(not any(p["mode"] == "car" and hh.member(a).zone == z for a, p in plan.items()))
        elif e == "no_trip":
            t = TARGETS[h]["no_trip"]
            res[e].append(plan[t]["mode"] is None if t in plan else not any(p["escort"] == t for p in plan.values()))
        elif e == "deadline_change":
            t = TARGETS[h]["deadline"]
            o = r["execution"]["outcomes"][t]
            res[e].append(not o["missed"] and o["late"] == 0)
    return {e: f"{sum(v)}/{len(v)}" for e, v in sorted(res.items())}


def _markdown(s: dict[str, Any]) -> str:
    t = s["table"]
    L = [f"# Experiment summary\n\nPaired instances: **{s['instances']}** (household x event x seed), "
         f"model: `{s['run_meta'].get('model', '?')}`, client config: `{s['run_meta'].get('client', {})}`.\n",
         "Regret = executed household generalized cost minus the oracle's (minutes-equivalent; lower is better). "
         "CI = 95% bootstrap over instances.\n",
         "| condition | regret (CI95) | on-time | missed | intent conflicts | committed violations | exec failures | msgs | deadlocks | LLM calls | invalid | fallbacks | tokens | LLM s |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c, r in t.items():
        L.append(f"| {c} | {r['regret_mean']} ({r['regret_ci95'][0]}, {r['regret_ci95'][1]}) | {r['on_time_rate']:.0%} | "
                 f"{r['missed_rate']:.0%} | {r['intent_conflicts_initial']} | {r['violations_committed']} | {r['exec_failures']} | "
                 f"{r['messages']} | {r['deadlocks']} | {r['llm_calls_mean']} | {r['llm_invalid']} | {r['fallback_decisions']} | "
                 f"{r['tokens_mean']} | {r['llm_latency_s_mean']} |")
    L += ["\n## Regret by event kind\n", "| condition | " + " | ".join(next(iter(s["regret_by_event_kind"].values()))) + " |",
          "|---|" + "---|" * 4]
    for c, r in s["regret_by_event_kind"].items():
        L.append(f"| {c} | " + " | ".join(str(v) for v in r.values()) + " |")
    L += ["\n## Regret by event\n", "| condition | " + " | ".join(EVENTS) + " |", "|---|" + "---|" * len(EVENTS)]
    for c, r in s["regret_by_event"].items():
        L.append(f"| {c} | " + " | ".join(str(v) for v in r.values()) + " |")
    L += ["\n## Paired comparisons (A minus B regret; negative = A better)\n",
          "| comparison | mean diff (CI95) | A better / tie / worse | unstructured events only |", "|---|---|---|---|"]
    for k, v in s["paired"].items():
        u = v.get("unstructured_only")
        L.append(f"| {k} | {v['mean_diff']} ({v['ci95'][0]}, {v['ci95'][1]}) | {v['better']} / {v['tie']} / {v['worse']} | "
                 + (f"{u['mean_diff']} ({u['ci95'][0]}, {u['ci95'][1]}), n={u['n']}" if u else "-") + " |")
    L += ["\n## Negative control: irrelevant news (decoy vs ordinary day)\n", "| condition | agents whose plan changed | mean cost delta |", "|---|---|---|"]
    for c, v in s["decoy_overreaction"].items():
        L.append(f"| {c} | {v['agents_changed_plan']} | {v['mean_cost_delta']} |")
    L += ["\n## Hybrid gate\n", "```json", json.dumps(s["hybrid"], indent=2), "```"]
    ev = sorted({e for v in s["uptake"].values() for e in v})
    L += ["\n## Text uptake: committed plan consistent with the text-only news\n",
          "| condition | " + " | ".join(ev) + " |", "|---|" + "---|" * len(ev)]
    for c, v in s["uptake"].items():
        L.append(f"| {c} | " + " | ".join(v.get(e, "-") for e in ev) + " |")
    L += ["\n## Interpreter accuracy (exact match with ground-truth effect)\n", "```json",
          json.dumps(s["interpretation_accuracy"], indent=2), "```"]
    return "\n".join(L) + "\n"


def _bar_svg(title: str, data: dict[str, float], unit: str, err: dict[str, list[float]] | None = None) -> str:
    w, h, pad, bw = 640, 300, 50, 50
    vmax = max([*data.values(), *[e[1] for e in (err or {}).values()], 1e-9]) * 1.1
    gap = (w - 2 * pad) / max(1, len(data))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="11">',
           f'<rect width="{w}" height="{h}" fill="white"/><text x="{w / 2}" y="18" text-anchor="middle" font-size="14">{title}</text>',
           f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#333"/>']
    for i, (k, v) in enumerate(data.items()):
        x = pad + i * gap + (gap - bw) / 2
        bh = (h - 2 * pad) * v / vmax
        color = "#888" if k in ("central", "oracle") else ("#2b6cb0" if k.endswith("on") else "#90cdf4")
        out.append(f'<rect x="{x:.1f}" y="{h - pad - bh:.1f}" width="{bw}" height="{bh:.1f}" fill="{color}"/>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{h - pad - bh - 4:.1f}" text-anchor="middle">{v:g}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{h - pad + 14}" text-anchor="middle">{k}</text>')
        if err and k in err:
            y1 = h - pad - (h - 2 * pad) * err[k][0] / vmax
            y2 = h - pad - (h - 2 * pad) * err[k][1] / vmax
            out.append(f'<line x1="{x + bw / 2:.1f}" y1="{y1:.1f}" x2="{x + bw / 2:.1f}" y2="{y2:.1f}" stroke="#000"/>')
    out.append(f'<text x="12" y="{h / 2}" transform="rotate(-90 12 {h / 2})" text-anchor="middle">{unit}</text></svg>')
    return "\n".join(out)


def _figures(s: dict[str, Any], d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    t = s["table"]
    (d / "regret.svg").write_text(_bar_svg("Mean regret vs oracle (95% CI)", {c: r["regret_mean"] for c, r in t.items()},
                                           "minutes-equivalent", {c: r["regret_ci95"] for c, r in t.items()}))
    (d / "llm_calls.svg").write_text(_bar_svg("LLM calls per episode", {c: r["llm_calls_mean"] for c, r in t.items()
                                                                         if c not in ("central", "oracle")}, "calls"))
    (d / "exec_failures.svg").write_text(_bar_svg("Execution failures per episode", {c: r["exec_failures"] for c, r in t.items()}, "failures"))
    (d / "missed.svg").write_text(_bar_svg("Missed activities (%)", {c: round(100 * r["missed_rate"], 1) for c, r in t.items()}, "%"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "analyze"])
    ap.add_argument("--out", default="results/runs.jsonl")
    ap.add_argument("--cache", default="results/llm_cache.jsonl")
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--model-filter", default=None, help="analyze only runs of this model (plus deterministic ones)")
    ap.add_argument("--seed-filter", type=int, nargs="+", default=None, help="analyze only these seeds")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--households", nargs="+", default=list(HOUSEHOLDS))
    ap.add_argument("--events", nargs="+", default=list(EVENTS))
    ap.add_argument("--policies", nargs="+", default=["rule", "llm", "hybrid", "interp", "central", "oracle"])
    args = ap.parse_args()
    run(args) if args.command == "run" else analyze(args)


if __name__ == "__main__":
    main()
