# HybridMobility-Coop

**Who takes the car, and who takes the child to school?** A small, reproducible benchmark of household agents that
share scarce resources under unexpected morning events. It compares **rule-based, LLM-based and hybrid** decision
engines, **with and without a decision-time negotiation protocol**, against a **central coordinator** and an
**oracle**.

> Independent prototype inspired by the 2027 CESI LINEACT / IRIT internship topic *Towards hybrid and communicative
> generative agents for simulating urban mobility behaviour*. Not affiliated with the laboratories, no code taken
> from their platform, no survey data used. Author: Youssef Dhouib (ISIMS, Sfax). It measures **coordination quality and cost, not behavioural realism**.

**Results page:** https://youssefdhouib.github.io/HybridMobility-Coop/ · **4-page project brief:** [`docs/HybridMobility-Coop_Brief.pdf`](docs/HybridMobility-Coop_Brief.pdf)

## Results at a glance

120 paired instances, qwen2.5:3b (local), regret = executed household cost minus the oracle's (minutes-equivalent, lower
is better), 95% bootstrap CI.

| engine (with communication) | regret | LLM calls / morning |
|---|---|---|
| Rules | 31.7 (20.0, 45.5) | 0 |
| LLM decides | 87.1 (65.9, 110.7) | 3.9 |
| Gated hybrid (LLM when free-text news arrives) | 61.5 (44.6, 79.6) | 2.4 |
| **LLM reads the news, rules decide** | **6.6 (2.6, 12.3)** | **0.62** |
| Central coordinator (same information, no agents) | 31.3 (19.3, 45.2) | 0 |

- Communication halves rule agents' regret (74.2 → 31.7) and makes them match the central coordinator on 118/120 instances.
- The small LLM decides worse than rules even on text-only events. Its reasons mention the news while its plans ignore it.
- Using the LLM only to translate news into a structured fact beats the coordinator (paired −24.8, CI −37.9 to −14.1). On
  held-out paraphrases the interpreter scored 74/80, including 20/20 adversarial decoys.

See [`docs/FINDINGS.md`](docs/FINDINGS.md) for the interpretation, [`results/summary.md`](results/summary.md) for every
number, and `results/report.html` for the visual report (all generated from `results/runs.jsonl`).

## What is in it

- **5 synthetic households**: one car or two; a flat-share; a grandmother who is the only driver; a single parent whose
  14-year-old can walk a sibling to school.
- **8 morning events**: an ordinary day; official events (bus strike, heavy rain) that the journey planner reflects;
  text-only events (car warning light, ring-road accident, school or workplace closed, earlier deadline) that exist only as
  a sentence; and an irrelevant newsletter as a negative control.
- **3 decision engines**: rules (habit + generalized cost); LLM (local qwen2.5:3b via Ollama, schema-constrained, validated,
  labelled fallback); hybrid (rules by default, LLM when free-text news arrives or the routine option is already late).
- **Communication off/on**: off means each member plans alone and conflicts surface at departure; on means a typed
  protocol (`inform, request, propose, counter, accept, reject, commit`) with bounded rounds and a logged deadlock
  tie-break.
- **Physical execution**: cars have a location over time, so a *planned* conflict is counted separately from a parent
  *finding the car gone*.
- **Baselines**: an exhaustive central coordinator with the same information, and an oracle that reads the ground truth.
- **Measured**: regret vs oracle, on-time and missed activities, planned conflicts, conflicts left after talking,
  execution failures, messages, deadlocks, LLM calls, invalid outputs, fallbacks, tokens, latency.

## Run it

Python 3.10+, standard library only. Ollama is needed only for the LLM and hybrid conditions.

```bash
git clone https://github.com/youssefdhouib/HybridMobility-Coop && cd HybridMobility-Coop
python3 -m unittest discover -s tests -t .          # 14 deterministic tests, no LLM needed

ollama pull qwen2.5:3b                                # optional: qwen3:4b for the sensitivity check
python3 -m hmcoop.experiments run --seeds 0 1 2       # about 12 min on an RTX 3050 laptop GPU (4 GB)
python3 -m hmcoop.experiments analyze                 # results/summary.md + figures
python3 -m hmcoop.report                              # results/report.html

# second model (same grid, LLM conditions only)
python3 -m hmcoop.experiments run --model qwen3:4b --policies llm hybrid
python3 -m hmcoop.experiments analyze --model-filter qwen3:4b
```

Replay a single morning and print its trace:

```bash
python3 -c "from hmcoop.episode import run_episode as r; import json; print(json.dumps(r('martin','bus_strike','rule',True)['messages'], indent=1))"
```

The LLM cache (`results/llm_cache.jsonl`) makes reruns reproducible. Cached calls keep their original latency and are
flagged. Delete it to query the model again.

## Documentation

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md): research questions, information design, protocol, baselines,
  statistics, threats to validity.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): module map and diagram, design choices, how it relates to the
  team's platform.
- [`docs/FINDINGS.md`](docs/FINDINGS.md): short research report.

## Limitations

Synthetic and uncalibrated travel times and cost weights; five households, one morning each, no memory; two small local
models at temperature 0; a typed negotiation rather than free dialogue; a hybrid gate that cannot judge relevance;
text-only events designed by the author. **Nothing here measures how human the decisions are.** That question
needs survey ground truth, as in Bru, Oberoi & Gaudou (2026).

## References

- Bru, Oberoi & Gaudou (2026). *Towards Adaptive and Real-Survey-Aligned Simulated Urban Mobility Behaviour of
  Generative Agents.* Preprint submitted to AAMAS 2027. [arXiv:2610.22407](https://arxiv.org/abs/2610.22407)
- Vu, Gaudou & Oberoi (2025). *Modeling realistic human behavior using generative agents in a multimodal transport
  system: Software architecture and Application to Toulouse.* [arXiv:2510.19497](https://arxiv.org/abs/2510.19497)
- Taillandier et al. (2025). *Integrating LLM in Agent-Based Social Simulation: Opportunities and Challenges.*
  [arXiv:2507.19364](https://arxiv.org/abs/2507.19364)
- Team platform: [Ytlse/generative-agents-urban-mobility](https://github.com/Ytlse/generative-agents-urban-mobility)

MIT licence (see `LICENSE`).
