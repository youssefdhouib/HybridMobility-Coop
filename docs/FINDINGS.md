# Findings: hybrid and communicating household agents on a coordination benchmark

Short research report. All numbers come from `results/summary.md` (qwen2.5:3b, 120 paired instances = 5 households
x 8 events x 3 seeds) and `results/heldout_qwen2.5_3b.json`. Regret is the executed household generalized cost minus
the oracle's, in minutes-equivalent (lower is better), with 95% bootstrap intervals. Scope reminder: this measures
coordination quality and cost under declared synthetic assumptions, **not** how human the decisions are.

## Key findings

The bullet list below is also the "Findings" block of the results page.

- **Talking fixes known conflicts, and rules are enough for that.** With communication, rule agents cut regret from 74.2 to 31.7 (paired difference -42.5, CI -64.2 to -24.2) and halve execution failures (0.56 to 0.25 per morning). They then match an exhaustive central coordinator with the same information on 118 of 120 instances. An LLM is not needed to negotiate the car or the school run when the situation is known.
- **The small LLM is a poor decision-maker, even where it should help.** qwen2.5:3b agents have higher regret than rules on every kind of event (87.1 vs 31.7 overall; 105.4 vs 62.7 on text-only events). Their reasons often mention the news ("the car is not reliable") while the plan ignores it: after a text-only car warning, only 3 of 15 committed plans avoided the car. In negotiation they rarely concede, which caused 9 deadlocks resolved by the protocol's logged tie-break.
- **Gating the LLM saves calls but not quality.** The event-gated hybrid uses 38% fewer LLM calls than the always-LLM agent (292 vs 468) and stays on rules on almost all ordinary and official-event days (5 escalations out of 45 such mornings). On text-only events, though, it inherits the LLM's mistakes. Irrelevant news also triggers the gate and changed 8 of 36 plans for the worse (+32 cost).
- **Letting the LLM read and the rules decide works best.** When the LLM only translates the free-text news into a structured fact once per household, and rules plus the protocol decide, regret drops to **6.6 (CI 2.6 to 12.3)**. That is lower than the central coordinator (paired -24.8; better on 44 instances, worse on 2). It uses 0.62 LLM calls per morning (84% fewer than the always-LLM agent) and leaves plans unchanged for irrelevant news (0 of 36 changed).
- **The interpreter generalises to wording it was not tuned on, mostly.** After one prompt revision on the scenario sentences (75/75 correct), it scored **74/80 on held-out paraphrases**, including 20/20 adversarial decoys that mention cars, schools or buses. Five of the six misses share one wording that requires converting a clock time ("be there by 07:15") into minutes.

## 1. Question

The 2027 internship asks for agents that use rules where they suffice and an LLM where they do not, and for agents
that coordinate decisions such as who takes the family car or the children to school. This benchmark isolates both
questions on a small, fully traceable problem. Households share scarce resources, and morning news either is
already in the journey planner (official events) or exists only as text.

## 2. Setup (details in METHODOLOGY.md)

- 5 synthetic households, 8 events (ordinary day; 2 official; 4 text-only; 1 irrelevant newsletter as negative control), 3 seeds.
- 4 engines x communication off/on, plus a central coordinator (same information) and an oracle (ground truth).
  The engines: rules; LLM decides; gated hybrid; LLM interprets the news and rules decide.
- Every engine sees the same planner table and the same news text.
- Execution is physical: cars have locations, and a second driver finds the car gone.
- LLM: qwen2.5:3b via Ollama, temperature 0, JSON-schema constrained decoding, every output validated. There were 0 invalid outputs out of
  1,384 calls. In the always-LLM condition, 13 negotiation replies were schema-valid but inconsistent (e.g. "concede"
  without an option) and were replaced by labelled rule fallbacks.

## 3. Results

| condition | regret (CI95) | missed activities | exec. failures / morning | LLM calls / morning | tokens / morning |
|---|---|---|---|---|---|
| Rules · no talk | 74.2 (52.8, 97.7) | 6.0% | 0.56 | 0 | 0 |
| Rules · talk | 31.7 (20.0, 45.5) | 3.0% | 0.25 | 0 | 0 |
| LLM decides · talk | 87.1 (65.9, 110.7) | 14.6% | 0.21 | 3.9 | 2,176 |
| Gated hybrid · talk | 61.5 (44.6, 79.6) | 11.9% | 0.21 | 2.4 | 1,411 |
| LLM reads news, rules decide · no talk | 49.0 (30.0, 70.4) | 4.6% | 0.27 | 0.62 | 322 |
| **LLM reads news, rules decide · talk** | **6.6 (2.6, 12.3)** | **1.4%** | **0.00** | **0.62** | **322** |
| Central coordinator | 31.3 (19.3, 45.2) | 3.5% | 0.25 | 0 | 0 |
| Oracle | 0 | 2.4% | 0.03 | 0 | 0 |

The full table, regret by event, all paired comparisons and the "does the plan follow the news" diagnostic are in
`results/summary.md`.

Where the remaining regret of the best engine comes from: three text-only events, namely the ring-road accident (20.6),
the earlier deadline (19.4) and the car warning (9.5). Its interpretations are correct in all of them, so this remainder
is the gap between habit-bound rule agents and an exhaustive oracle. For the earlier deadline, being on time is often
impossible whatever the plan: even the oracle is on time in only 8 of 15 cases.

## 4. Interpretation

1. **Separate understanding from deciding.** In this setting the LLM's value lies in turning open text into state the
   rest of the system already knows how to use. Asking a 3B model to also weigh deadlines, costs and family duties
   produced worse plans than a ten-line heuristic. This matches the motivation in Bru, Oberoi & Gaudou (2026) for
   reserving generative reasoning for situations that fixed rules or fitted models cannot represent. It suggests that
   the trigger should be *unrepresented information*, and the LLM's job should be *translation*, rather than a full
   handover of the decision.
2. **Communication and LLMs answer different problems.** Communication removes coordination failures (who drives,
   who accompanies). Text understanding removes information failures (a broken car the planner doesn't know about).
   The best condition needs both: removing communication from the interpreter engine raises regret from 6.6 to 49.0.
3. **A strong deterministic baseline changes the story.** Without the central coordinator, "LLM agents that talk"
   would look like an improvement over "LLM agents that don't" (87 vs 161). With it, the honest summary is that the
   protocol, not the LLM, does the coordinating.

## 5. Threats to validity

- **Best case for the interpreter.** Its vocabulary is exactly the set of effects the simulator can produce. Real
  news can imply effects outside any fixed vocabulary; here those would map to `none`.
- **The author wrote the scenarios and the held-out paraphrases.** The ordinary, official and decoy conditions bound the
  bias towards text understanding, and the held-out set was written after the prompt was frozen. Still, it is
  not an independent test set.
- **Prompt sensitivity.** The decision prompts were not tuned; the interpreter prompt was revised once. A tuned
  decision prompt could narrow the gap. Bru et al. (2026) show that prompt tuning matters for mode-choice alignment.
- **Small models, temperature 0.** Each LLM row is one deterministic policy per model. The qwen3:4b check (section 6)
  covers one seed only.
- **Synthetic world.** Invented travel times and cost weights (declared in `model.py`), one morning per household,
  no memory. The ranking of engines could change under other weights. This is a reason to run the same protocol
  inside a calibrated simulator, not a result about Toulouse.
- **An earlier run had a flawed oracle** (it could leave a child unaccompanied when that was cheaper). It was found
  by inspecting the results, fixed, and every condition was re-run. The first run is archived with an explanation in
  `results/archive/`.

## 6. Second model (qwen3:4b, seed 0, 40 paired instances)

Same protocol, LLM-based engines only, on the 40 seed-0 instances, paired with qwen2.5:3b on the same instances
(`results/summary_qwen3_4b_seed0.md`, `results/summary_seed0.md`).

| engine (with communication) | qwen2.5:3b | qwen3:4b |
|---|---|---|
| LLM decides | 56.6 | 31.3 (CI 19.9 to 44.2) |
| Gated hybrid | 36.3 | 28.8 |
| LLM reads news, rules decide | 1.5 | 1.5 |
| Rules (reference, no LLM) | 19.8 | 19.8 |

- The larger model is a much better decision-maker (56.6 to 31.3) but still worse than rules on the same instances
  (paired +11.5, CI 5.0 to 19.3; worse on 20, better on 1). It deadlocked more often in car negotiation (11 vs 3 for
  qwen2.5 on the same 40 instances), and 3 of its outputs were invalid, all replaced by labelled fallbacks.
- As an interpreter it produced the same facts as qwen2.5 on every scenario, so the interpreter engine's result is
  identical. On the held-out paraphrases it scored 75/80. All 5 misses named the right member and effect but gave
  0 minutes for "be there by 07:15", and the validator rejected them.
- The qualitative ranking (interpreter hybrid < rules = coordinator < LLM-based deciders) holds for both models.

## 7. What I would do next, inside the team's platform

1. Put the interpreter step between news or observation and the controller's feasibility filter, so text-only events
   update vehicle availability, activity cancellation or deadlines before itineraries are enumerated.
2. Add the household protocol between itinerary enumeration and the probabilistic choice, for members holding
   conflicting claims on a household vehicle or a child's trip.
3. Evaluate both against the EMC² survey at the aggregate and trip level, as in the 2026 paper. That is the step
   this benchmark cannot take: it would show whether better coordination also means more realistic behaviour.
