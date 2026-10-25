"""Build the static results page (results/report.html) from experiment outputs only.

    python3 -m hmcoop.report

Every number on the page is read from results/summary*.json and results/runs.jsonl; the only hand-written
text is docs/FINDINGS.md (the interpretation) and the fixed explanatory copy below.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
E = html.escape

LABELS = {"rule-off": "Rules · no talk", "rule-on": "Rules · talk", "llm-off": "LLM · no talk", "llm-on": "LLM · talk",
          "hybrid-off": "Hybrid · no talk", "hybrid-on": "Hybrid · talk",
          "interp-off": "LLM reads news, rules decide · no talk", "interp-on": "LLM reads news, rules decide · talk",
          "central": "Central coordinator",
          "oracle": "Oracle (upper bound)"}
KIND_LABEL = {"none": "Ordinary day", "structured": "Official events", "unstructured": "Text-only events",
              "decoy": "Irrelevant news"}
PERF_CLASS = {"inform": "p-inform", "request": "p-request", "propose": "p-propose", "counter": "p-counter",
              "accept": "p-accept", "reject": "p-reject", "commit": "p-commit"}

CSS = """
/* Layout: one reading column, wide figures break out into a scroll box; transit-signage look. */
:root {
  --bg: #f6f7f9; --surface: #ffffff; --ink: #14202e; --muted: #5b6878; --line: #d8dde4;
  --talk: #1f5fa8; --notalk: #8fb3dc; --base: #7a8594; --bad: #b3261e; --good: #1e7a46; --warn: #a15c00;
  --chip: #eef2f7;
  --f-display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --f-body: "IBM Plex Sans", system-ui, sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f151c; --surface: #17202a; --ink: #e6ebf1; --muted: #9aa7b6; --line: #2a3644;
  --talk: #6ea8ec; --notalk: #34557c; --base: #7d8897; --bad: #f2867e; --good: #6fcf97; --warn: #f0b35a;
  --chip: #1f2a36; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0f151c; --surface: #17202a; --ink: #e6ebf1; --muted: #9aa7b6; --line: #2a3644;
  --talk: #6ea8ec; --notalk: #34557c; --base: #7d8897; --bad: #f2867e; --good: #6fcf97; --warn: #f0b35a;
  --chip: #1f2a36; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--f-body); font-size: 16px; line-height: 1.55; }
.wrap { max-width: 980px; margin: 0 auto; padding-block: 40px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 44px; }
.prose { max-width: 68ch; }
h1, h2, h3 { font-family: var(--f-display); text-wrap: balance; line-height: 1.15; margin: 0; }
h1 { font-size: clamp(2rem, 5vw, 3rem); font-weight: 600; letter-spacing: -0.01em; }
h2 { font-size: 1.6rem; font-weight: 600; }
h3 { font-size: 1.1rem; font-weight: 600; }
section { display: grid; gap: 16px; }
p { margin: 0; }
.eyebrow { font-family: var(--f-mono); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.lede { font-size: 1.15rem; color: var(--ink); }
.muted { color: var(--muted); }
.line-badge { display: inline-flex; gap: 8px; flex-wrap: wrap; }
.line-badge span { font-family: var(--f-mono); font-size: 0.75rem; padding: 3px 8px; border-radius: 3px; background: var(--chip); color: var(--muted); }
.findings { display: grid; gap: 12px; padding: 0; margin: 0; list-style: none; counter-reset: f; }
.findings li { display: grid; grid-template-columns: 2.2rem 1fr; gap: 8px; align-items: baseline; }
.findings li::before { counter-increment: f; content: counter(f); font-family: var(--f-display); font-weight: 600;
  width: 1.7rem; height: 1.7rem; display: grid; place-items: center; border-radius: 50%; background: var(--talk); color: var(--surface); font-size: 0.95rem; }
.scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 0.86rem; font-variant-numeric: tabular-nums; }
th, td { padding: 8px 10px; text-align: right; border-bottom: 1px solid var(--line); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
thead th { font-family: var(--f-mono); font-weight: 500; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
tr.base td { color: var(--muted); }
td.hi { color: var(--bad); font-weight: 600; }
td.lo { color: var(--good); font-weight: 600; }
figure { margin: 0; display: grid; gap: 8px; }
figcaption { font-size: 0.85rem; color: var(--muted); max-width: 68ch; }
svg text { fill: var(--ink); font-family: var(--f-mono); font-size: 11px; }
svg .axis { stroke: var(--line); }
svg .talk { fill: var(--talk); } svg .notalk { fill: var(--notalk); } svg .base { fill: var(--base); }
svg .err { stroke: var(--ink); stroke-width: 1.2; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.cols > * { min-width: 0; }
.trace { display: grid; gap: 6px; font-size: 0.86rem; }
.msg { display: grid; grid-template-columns: 5.5rem 6rem 1fr; gap: 8px; align-items: baseline; padding: 6px 0; border-bottom: 1px dashed var(--line); }
.msg .who { font-weight: 600; }
.perf { font-family: var(--f-mono); font-size: 0.7rem; padding: 2px 6px; border-radius: 3px; background: var(--chip); justify-self: start; }
.p-counter, .p-reject { color: var(--warn); } .p-accept, .p-commit { color: var(--good); } .p-request { color: var(--talk); }
.src { font-family: var(--f-mono); font-size: 0.68rem; color: var(--muted); margin-left: 6px; }
.src.llm { color: var(--talk); } .src.fallback, .src.protocol { color: var(--warn); }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px; display: grid; gap: 10px; }
.outcome { font-size: 0.86rem; display: grid; gap: 4px; }
.outcome .bad { color: var(--bad); } .outcome .ok { color: var(--good); }
.limits { display: grid; gap: 8px; padding-left: 1.1rem; margin: 0; }
details summary { cursor: pointer; color: var(--muted); font-size: .9rem; }
code { font-family: var(--f-mono); font-size: .85em; }
a { color: var(--talk); }
a:focus-visible { outline: 2px solid var(--talk); outline-offset: 2px; }
@media (max-width: 560px) { .msg { grid-template-columns: 1fr; gap: 2px; } }
"""


def _fmt(v: Any) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else E(str(v))


def regret_chart(table: dict[str, Any]) -> str:
    items = list(table.items())
    w, h, left, bottom, top = 820, 360, 270, 30, 16
    vmax = max(max(r["regret_ci95"][1], r["regret_mean"]) for _, r in items) * 1.1 or 1
    row = (h - top - bottom) / len(items)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Mean regret by condition">']
    for i, (c, r) in enumerate(items):
        y = top + i * row
        bw = (w - left - 60) * r["regret_mean"] / vmax
        cls = "base" if c in ("central", "oracle") else ("talk" if c.endswith("on") else "notalk")
        out.append(f'<text x="{left - 8}" y="{y + row * 0.62:.1f}" text-anchor="end">{E(LABELS[c])}</text>')
        out.append(f'<rect class="{cls}" x="{left}" y="{y + row * 0.18:.1f}" width="{max(bw, 1):.1f}" height="{row * 0.64:.1f}" rx="2"/>')
        lo = left + (w - left - 60) * r["regret_ci95"][0] / vmax
        hi = left + (w - left - 60) * r["regret_ci95"][1] / vmax
        out.append(f'<line class="err" x1="{lo:.1f}" x2="{hi:.1f}" y1="{y + row / 2:.1f}" y2="{y + row / 2:.1f}"/>')
        out.append(f'<text x="{max(hi, left + bw) + 6:.1f}" y="{y + row * 0.62:.1f}">{r["regret_mean"]:g}</text>')
    out.append(f'<line class="axis" x1="{left}" x2="{left}" y1="{top}" y2="{h - bottom}"/>')
    out.append(f'<text x="{left}" y="{h - 8}">0</text><text x="{w - 60}" y="{h - 8}" text-anchor="end">{vmax:.0f} min-eq.</text>')
    out.append("</svg>")
    return "".join(out)


def kind_table(by_kind: dict[str, dict[str, float]]) -> str:
    kinds = list(next(iter(by_kind.values())))
    rows = []
    for c, vals in by_kind.items():
        cells = "".join(f"<td>{vals[k]:g}</td>" for k in kinds)
        rows.append(f'<tr class="{"base" if c in ("central", "oracle") else ""}"><td>{E(LABELS[c])}</td>{cells}</tr>')
    head = "".join(f"<th>{E(KIND_LABEL.get(k, k))}</th>" for k in kinds)
    return f'<div class="scroll"><table><thead><tr><th>Condition</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def main_table(table: dict[str, Any]) -> str:
    cols = [("regret_mean", "Regret"), ("on_time_rate", "On time"), ("missed_rate", "Missed"),
            ("intent_conflicts_initial", "Planned conflicts"), ("violations_committed", "Left after talk"),
            ("exec_failures", "Exec. failures"), ("messages", "Messages"), ("deadlocks", "Deadlocks"),
            ("llm_calls_mean", "LLM calls"), ("llm_invalid", "Invalid"), ("tokens_mean", "Tokens"),
            ("llm_latency_s_mean", "LLM s")]
    head = "".join(f"<th>{E(n)}</th>" for _, n in cols)
    rows = []
    for c, r in table.items():
        cells = []
        for k, _ in cols:
            v = r[k]
            if k in ("on_time_rate", "missed_rate"):
                cells.append(f"<td>{v:.0%}</td>")
            else:
                cells.append(f"<td>{_fmt(v)}</td>")
        rows.append(f'<tr class="{"base" if c in ("central", "oracle") else ""}"><td>{E(LABELS[c])}</td>{"".join(cells)}</tr>')
    return f'<div class="scroll"><table><thead><tr><th>Condition</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def paired_table(paired: dict[str, Any]) -> str:
    rows = []
    for k, v in paired.items():
        a, b = k.split(" vs ")
        u = v.get("unstructured_only")
        cls = "lo" if v["ci95"][1] < 0 else ("hi" if v["ci95"][0] > 0 else "")
        rows.append(f"<tr><td>{E(LABELS[a])} vs {E(LABELS[b])}</td><td class='{cls}'>{v['mean_diff']:g}</td>"
                    f"<td>{v['ci95'][0]:g} to {v['ci95'][1]:g}</td><td>{v['better']} / {v['tie']} / {v['worse']}</td>"
                    f"<td>{(str(u['mean_diff']) + ' (' + str(u['ci95'][0]) + ' to ' + str(u['ci95'][1]) + ')') if u else '-'}</td></tr>")
    return ('<div class="scroll"><table><thead><tr><th>A vs B</th><th>Mean diff</th><th>95% CI</th>'
            '<th>A better / tie / worse</th><th>Text-only events</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def trace_panel(run: dict[str, Any], title: str) -> str:
    msgs = []
    for m in run["messages"]:
        src = m["source"]
        msgs.append(f'<div class="msg"><span class="who">{E(m["sender"])}</span><span class="perf {PERF_CLASS.get(m["performative"], "")}">'
                    f'{E(m["performative"])}</span><span>{E(m["text"])}<span class="src {E(src)}">{E(src)}</span></span></div>')
    outs = []
    for mid, o in run["execution"]["outcomes"].items():
        if not o["has_activity"]:
            outs.append(f'<div>{E(mid)}: no activity today</div>')
            continue
        status = '<span class="bad">missed</span>' if o["missed"] else (
            f'<span class="bad">{o["late"]} min late</span>' if o["late"] else '<span class="ok">on time</span>')
        outs.append(f'<div><b>{E(mid)}</b>: {E(o["mode"] or "did not travel")} · {status}'
                    + (f' <span class="muted">({E("; ".join(o["notes"]))})</span>' if o["notes"] else "") + "</div>")
    log = "".join(f"<div class='muted'>{E(x)}</div>" for x in run["execution"]["log"]) or "<div class='muted'>No execution problems.</div>"
    m = run["metrics"]
    return (f'<div class="panel"><h3>{E(title)}</h3><p class="muted">Regret {m["regret"]:g} · LLM calls {m["llm_calls"]} · '
            f'messages {m["messages"]}</p>'
            + (f'<div class="trace">{"".join(msgs)}</div>' if msgs else '<p class="muted">No messages: each member planned alone.</p>')
            + f'<div class="outcome">{"".join(outs)}</div>{log}</div>')


def build() -> Path:
    s = json.loads((RES / "summary.json").read_text())
    runs = [json.loads(l) for l in (RES / "runs.jsonl").read_text().splitlines()]
    find = {(r["household"], r["event"], r["seed"], r["condition"], r.get("model")): r for r in runs}
    model = s["run_meta"].get("model", "qwen2.5:3b")
    alt = sorted(p for p in RES.glob("summary_*.json") if not p.stem.startswith("summary_seed"))
    findings_md = (ROOT / "docs" / "FINDINGS.md").read_text() if (ROOT / "docs" / "FINDINGS.md").exists() else ""
    key = findings_md.split("## Key findings", 1)[-1].split("\n## ", 1)[0] if findings_md else ""
    findings = [l[2:].strip() for l in key.splitlines() if l.startswith("- ")]

    def fx(line: str) -> str:  # tiny markdown: **bold**
        parts = E(line).split("**")
        return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))

    ex = [("martin", "bus_strike", 0, "rule-off", None, "Rules, no talk"),
          ("martin", "bus_strike", 0, "rule-on", None, "Rules, talk"),
          ("martin", "bus_strike", 0, "llm-on", model, f"LLM ({model}), talk")]
    ex2 = [("martin", "car_breakdown", 0, "rule-on", None, "Rules, talk"),
           ("martin", "car_breakdown", 0, "llm-on", model, f"LLM ({model}), talk")]
    panels = "".join(trace_panel(find[k[:5]], k[5]) for k in ex if k[:5] in find)
    panels2 = "".join(trace_panel(find[k[:5]], k[5]) for k in ex2 if k[:5] in find)
    news = next((r["event_text"] for r in runs if r["household"] == "martin" and r["event"] == "car_breakdown"), "")

    alt_html = ""
    for p in alt:
        a = json.loads(p.read_text())
        m2 = a["run_meta"].get("model", p.stem)
        # pair on the same instances: the second model ran a seed subset
        sub = p.stem.split("_seed")[-1] if "_seed" in p.stem else None
        ref = json.loads((RES / f"summary_seed{sub}.json").read_text()) if sub and (RES / f"summary_seed{sub}.json").exists() else s
        rows = "".join(f"<tr><td>{E(LABELS[c])}</td><td>{ref['table'][c]['regret_mean']:g}</td><td>{a['table'][c]['regret_mean']:g}</td>"
                       f"<td>{a['regret_by_event_kind'][c].get('unstructured', 0):g}</td><td>{a['table'][c]['llm_invalid']}</td>"
                       f"<td>{a['table'][c]['deadlocks']}</td><td>{a['table'][c]['llm_latency_s_mean']:g}</td></tr>"
                       for c in a["table"] if c.startswith(("llm", "hybrid", "interp")) and c in ref["table"])
        alt_html += (f"<section><p class='eyebrow'>Sensitivity</p><h2>Same grid, second model: {E(m2)}</h2>"
                     f"<p class='prose muted'>Paired on the same {a['instances']} instances (seed 0). Deterministic conditions are identical by construction; only the LLM-based rows change.</p>"
                     f"<div class='scroll'><table><thead><tr><th>Condition</th><th>Regret {E(model)}</th><th>Regret {E(m2)}</th>"
                     f"<th>{E(m2)} text-only</th><th>Invalid</th><th>Deadlocks</th><th>LLM s / episode</th></tr></thead>"
                     f"<tbody>{rows}</tbody></table></div></section>")

    hy = s.get("hybrid", {})
    hy_rows = "".join(f"<tr><td>{E(LABELS[c])}</td><td>{v['episodes_with_escalation']} / {v['episodes']}</td>"
                      f"<td>{v['escalations_on_ordinary_or_structured_days']}</td><td>{v['llm_calls_total']}</td>"
                      f"<td>{v[[k for k in v if k.startswith('llm-')][0]]}</td></tr>" for c, v in hy.items())
    dec_rows = "".join(f"<tr><td>{E(LABELS[c])}</td><td>{E(v['agents_changed_plan'])}</td><td>{v['mean_cost_delta']:g}</td></tr>"
                       for c, v in s["decoy_overreaction"].items() if c not in ("central", "oracle"))

    up = s.get("uptake", {})
    evs = sorted({e for v in up.values() for e in v})
    ev_names = {"car_breakdown": "Car warning light", "deadline_change": "Earlier deadline", "no_trip": "Activity cancelled",
                "ringroad_accident": "Ring-road accident"}
    up_rows = "".join(f"<tr class='{'base' if c in ('central', 'oracle') else ''}'><td>{E(LABELS[c])}</td>"
                      + "".join(f"<td>{E(v.get(e, '-'))}</td>" for e in evs) + "</tr>" for c, v in up.items())
    uptake_html = (f"<section><p class='eyebrow'>Diagnosis</p><h2>Does the committed plan follow the news?</h2>"
                   f"<p class='prose'>For each text-only event, a plan is counted as consistent when it does what the news implies: no more drivers than "
                   f"working cars, no car trip into the blocked district, nobody travelling to a cancelled activity, and the member with the earlier "
                   f"deadline arriving on time. Rules and the central coordinator cannot read the news, so their score is the base rate.</p>"
                   f"<div class='scroll'><table><thead><tr><th>Condition</th>{''.join(f'<th>{E(ev_names.get(e, e))}</th>' for e in evs)}</tr></thead>"
                   f"<tbody>{up_rows}</tbody></table></div></section>") if up else ""
    held = sorted(RES.glob("heldout_*.json"))
    held_html = ""
    if held:
        typ_names = {"car_breakdown": "Car unusable", "ringroad": "Road delay", "no_trip": "Activity cancelled",
                     "deadline": "Earlier deadline", "decoy": "Irrelevant (adversarial)"}
        hs = [json.loads(p.read_text()) for p in held]
        types = list(hs[0]["by_type"])
        head = "".join(f"<th>{E(h['model'])}</th>" for h in hs)
        body = "".join(f"<tr><td>{E(typ_names.get(t, t))}</td>" + "".join(f"<td>{E(h['by_type'][t]['exact'])}</td>" for h in hs) + "</tr>"
                       for t in types)
        body += "<tr><td><b>All</b></td>" + "".join(f"<td><b>{h['exact']}/{h['n']}</b></td>" for h in hs) + "</tr>"
        dev = s.get("interpretation_accuracy", {}).get("interp-on", {})
        dev_txt = ", ".join(f"{k} {v}" for k, v in dev.items())
        misses = [r for h in hs for r in h["rows"] if not r["exact"]][:6]
        miss_html = "".join(f"<li><span class='muted'>{E(r['household'])}</span> “{E(r['text'])}” → <code>{E(str(r['answer'].get('effect')))}</code>"
                            f"{(' / ' + E(str(r['answer'].get('member')))) if r['answer'].get('member') not in (None, 'none') else ''}</li>" for r in misses)
        held_html = (f"<section><p class='eyebrow'>Held-out test</p><h2>Can the model read news it was not tuned on?</h2>"
                     f"<p class='prose'>The interpreter prompt was revised once, on the scenario sentences themselves (development accuracy after the "
                     f"revision: {E(dev_txt) or 'see summary'}). It was then frozen. The table below uses paraphrases written afterwards and never "
                     f"used for prompt development, including decoys that mention cars, schools or buses without changing today's trips. "
                     f"Exact match on effect type and target.</p>"
                     f"<div class='scroll'><table><thead><tr><th>News type</th>{head}</tr></thead><tbody>{body}</tbody></table></div>"
                     + (f"<details><summary>Some misses</summary><ul class='limits'>{miss_html}</ul></details>" if miss_html else "")
                     + "</section>")
    heldout_html = held_html

    page = f"""<title>HybridMobility-Coop</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>{CSS}</style>
<main class="wrap">
<header style="display:grid;gap:14px">
  <p class="eyebrow">Independent research prototype · inspired by the CESI-LINEACT / IRIT 2027 internship topic</p>
  <h1>HybridMobility-Coop: who takes the car, and who takes the child to school?</h1>
  <p class="lede prose">A small, reproducible benchmark of household agents that share one car and the job of accompanying a child,
  facing unexpected morning events. It compares rule-based, LLM-based and hybrid decision engines, with and without a
  decision-time negotiation protocol, against a central coordinator and an oracle. A fourth engine lets the LLM only
  translate the free-text news into a structured fact and leaves the decisions to rules and the protocol.</p>
  <div class="line-badge"><span>{s['instances']} paired instances</span><span>10 conditions</span><span>LLM: {E(model)} via Ollama (local)</span>
  <span>temperature 0 · constrained JSON</span><span>4 decision engines</span><span>synthetic data · not survey-calibrated</span></div>
  <p class="muted" style="font-size:.9rem">By Youssef Dhouib · Code, data and 4-page brief:
  <a href="https://github.com/youssefdhouib/HybridMobility-Coop">github.com/youssefdhouib/HybridMobility-Coop</a></p>
</header>

<section>
  <p class="eyebrow">What this measures</p>
  <h2>Coordination quality and cost, not realism</h2>
  <p class="prose">The research this builds on (Vu, Gaudou &amp; Oberoi 2025; Bru, Oberoi &amp; Gaudou 2026) evaluates whether generative
  agents behave like real Toulouse travellers. This prototype asks a narrower question: when members must share scarce resources
  and the news changes the situation, which engine coordinates best, how much does talking help, and what does the LLM cost?
  <b>Regret</b> is the household's executed generalized cost (minutes-equivalent) minus the oracle's. A high-regret plan can still
  be a perfectly human one; testing human-likeness needs survey data this prototype does not have.</p>
</section>

<section>
  <p class="eyebrow">Findings</p>
  <h2>What the experiment shows</h2>
  <ol class="findings prose">{''.join(f'<li><span>{fx(f)}</span></li>' for f in findings)}</ol>
</section>

<section>
  <p class="eyebrow">Main result</p>
  <h2>Regret by condition</h2>
  <figure><div class="scroll" style="padding:8px">{regret_chart(s['table'])}</div>
  <figcaption>Mean regret over {s['instances']} paired instances, with 95% bootstrap intervals. Dark blue: with communication; light blue: without;
  grey: baselines (no agents, no messages).</figcaption></figure>
  {main_table(s['table'])}
  <p class="muted prose" style="font-size:.86rem">Planned conflicts: incompatible intentions in the first proposals (car over-claimed, child with no companion or two).
  Left after talk: conflicts still in the committed plan. Exec. failures: what physically went wrong at departure time
  (car gone or broken, child left behind, duplicate companion, trip to a closed place). Invalid: LLM outputs rejected by the validator.</p>
</section>

<section>
  <p class="eyebrow">Where the engines differ</p>
  <h2>Regret by kind of event</h2>
  <p class="prose">Official events are already reflected in the journey planner that every engine sees. Text-only events exist only as a
  news sentence, which rules cannot read. Irrelevant news is a negative control.</p>
  {kind_table(s['regret_by_event_kind'])}
</section>

<section>
  <p class="eyebrow">Paired comparisons</p>
  <h2>Same instance, two conditions</h2>
  <p class="prose muted">Negative difference = A has lower regret. Coloured when the 95% interval excludes zero.</p>
  {paired_table(s['paired'])}
</section>

<section class="cols">
  <div style="display:grid;gap:12px;align-content:start"><p class="eyebrow">Cost of the LLM</p><h3>Hybrid gate</h3>
  <div class="scroll"><table><thead><tr><th>Condition</th><th>Escalated episodes</th><th>On ordinary/official days</th><th>Calls</th><th>Always-LLM calls</th></tr></thead>
  <tbody>{hy_rows}</tbody></table></div></div>
  <div style="display:grid;gap:12px;align-content:start"><p class="eyebrow">Negative control</p><h3>Does irrelevant news change plans?</h3>
  <div class="scroll"><table><thead><tr><th>Condition</th><th>Members who changed plan</th><th>Cost change</th></tr></thead>
  <tbody>{dec_rows}</tbody></table></div></div>
</section>

{uptake_html}

{heldout_html}

<section>
  <p class="eyebrow">Replay · Martin family · bus strike (official) · seed 0</p>
  <h2>One morning, three ways</h2>
  <p class="prose">One car, two parents, an 8-year-old who must be accompanied and a cycling teenager. The bus strike pushes Marie,
  who usually takes the bus, towards the car that Paul needs for the school run.</p>
  <div class="cols">{panels}</div>
</section>

<section>
  <p class="eyebrow">Replay · Martin family · car warning light (text only) · seed 0</p>
  <h2>News that only exists as text</h2>
  <p class="prose">News: <i>{E(news)}</i> The planner still lists the car as available.</p>
  <div class="cols">{panels2}</div>
</section>

{alt_html}

<section>
  <p class="eyebrow">Limits</p>
  <h2>What this prototype does not show</h2>
  <ul class="limits prose">
    <li>Nothing about behavioural realism: there is no survey ground truth, and travel times and cost weights are invented and declared.</li>
    <li>Five hand-made households, one morning each, no memory or habit formation across days.</li>
    <li>The text-only events were designed by the author and reward reading text by construction; the ordinary, official and decoy conditions bound that bias.</li>
    <li>Two small local models at temperature 0: each LLM row is one deterministic policy, not a distribution over generations.</li>
    <li>The negotiation is typed (keep/concede, accept/decline + option ID), not free dialogue. That keeps outputs checkable but limits what persuasion can do.</li>
    <li>No GAMA, OpenTripPlanner or GTFS integration: the decision and protocol layer is built so it could sit behind a GAMA-to-Python service boundary like the one in the 2026 platform, but that is future work.</li>
  </ul>
</section>

<section>
  <p class="eyebrow">Sources</p>
  <ul class="limits prose" style="font-size:.9rem">
    <li>Bru, Oberoi &amp; Gaudou (2026). Towards Adaptive and Real-Survey-Aligned Simulated Urban Mobility Behaviour of Generative Agents. Preprint submitted to AAMAS 2027. <a href="https://arxiv.org/abs/2610.22407">arXiv:2610.22407</a></li>
    <li>Vu, Gaudou &amp; Oberoi (2025). Modeling realistic human behavior using generative agents in a multimodal transport system. <a href="https://arxiv.org/abs/2510.19497">arXiv:2510.19497</a></li>
    <li>Public research platform: <a href="https://github.com/Ytlse/generative-agents-urban-mobility">Ytlse/generative-agents-urban-mobility</a>. No code was copied from it.</li>
    <li>Taillandier et al. (2025). Integrating LLM in Agent-Based Social Simulation: Opportunities and Challenges. <a href="https://arxiv.org/abs/2507.19364">arXiv:2507.19364</a></li>
  </ul>
</section>
</main>
"""
    out = RES / "report.html"
    out.write_text(page)
    # Standalone copy served by GitHub Pages at the repository root.
    head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    title, rest = page.split("\n", 1)
    (ROOT / "index.html").write_text(head + title + "\n</head>\n<body style=\"margin:0\">\n" + rest + "\n</body>\n</html>\n")
    return out


if __name__ == "__main__":
    print(build())
