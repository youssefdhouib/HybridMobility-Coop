# Methodology

## 1. Scope: coordination, not behavioural realism

The research line this POC is inspired by (Vu, Gaudou & Oberoi 2025; Bru, Oberoi & Gaudou 2026) asks whether
generative agents behave **like real travellers**, and evaluates that against the Toulouse EMC² survey.
This POC asks a narrower, complementary question that the 2027 internship topic opens up:

> When household members must share scarce resources (a car, the job of accompanying a child) and the morning
> brings unexpected information, how do rule-based, LLM-based and hybrid agents perform **as coordinators**,
> with and without decision-time communication, and at what inference cost?

It therefore measures **feasibility, coordination quality and cost**. It does **not** measure human-likeness.
A "worse" plan in this benchmark may be a perfectly human one. Testing realism needs survey ground truth, which
this POC does not have and does not claim.

## 2. Research questions (falsifiable)

- **RQ1 (communication).** Does a decision-time protocol reduce resource conflicts, execution failures and
  regret compared with independent planning, for each decision engine? *Falsified if* communication-on shows no
  reduction in execution failures or regret over paired instances.
- **RQ2 (hybrid).** Does an event-gated hybrid keep the LLM's benefit on text-only events while making far fewer
  LLM calls than an always-LLM agent? *Falsified if* the hybrid's regret on text-only events is significantly worse
  than LLM-only, or its call savings are negligible.
- **RQ3 (trade-offs).** Where do LLM agents help or hurt compared with rules and with a deterministic central
  coordinator that has the same information? We explicitly expect the coordinator to win on known
  (structured) events; the question is whether text understanding pays for its cost on text-only ones.

## 3. Environment

- Five synthetic households (one with two cars, a flat-share without children, a grandmother who is the only
  driver, a single parent with a 14-year-old who can accompany a sibling, ...). Zone names evoke Toulouse
  districts only for readability; **travel times are invented**.
- One morning departure per member. Young children cannot travel alone and need an accompanying member, which adds a
  declared detour.
- **Cars are physical objects with a location.** At execution, members depart in time order; a car can only be
  taken if one is parked and working at home. A second driver finds it gone and re-plans on the spot (+5 min), and
  a broken car costs +10 min to discover. This keeps the *intent conflicts* that were planned apart from the
  *execution failures* that actually happened.
- Household welfare = generalized cost in minutes-equivalent (travel time + preferences + 3 min/EUR +
  4x lateness + 90 per missed adult activity, 240 for a young child left behind or more than 30 min late). All weights are
  declared in `hmcoop/model.py` and are **not estimated**. The child weight was raised from 90 to 240 after the first run
  showed the oracle "optimally" leaving an 8-year-old at home; that run is archived in `results/archive/` with an
  explanation, and every condition was re-run.

## 4. Events and the information design (fairness)

Every policy sees **exactly the same information**: (a) the journey-planner option table, which reflects only
*structured* (officially published) events, and (b) the raw free-text news. Policies differ only in what they can
do with that information.

| kind | events | planner reflects it? |
|---|---|---|
| none | ordinary day | n/a |
| structured | bus strike, heavy rain | yes |
| unstructured (text only) | car warning light, ring-road accident towards one district, school or workplace closed, earlier deadline for one member | no |
| decoy (negative control) | irrelevant town-hall newsletter | no (no effect) |

The car-warning event mirrors the "engine noise" experiment of Bru et al. (2026). The decoy is a negative
control: a good agent should not change its plan.

**Threat to validity:** I designed the text-only events, and they reward reading text by construction. The
ordinary-day, structured and decoy conditions bound this bias; results on text-only events should be read as
"can the model use the information when it is there", not as a natural frequency of such events.

## 5. Decision engines

- **Rule**: habit (who usually accompanies the child) + lowest generalized cost over the planner's options. It cannot
  interpret free text.
- **LLM**: qwen2.5:3b via local Ollama, temperature 0, fixed seed, JSON-schema constrained decoding (option IDs as
  an enum). It sees persona, habit, household constraints, news, messages and the option table. Every output is
  validated; invalid output is replaced by a **labelled** rule fallback and counted.
- **Interpreter hybrid (`interp`)**: the LLM never chooses a travel option. When free-text news is present it is called
  **once per household** to map the news onto the planner's fixed vocabulary of state changes (`none, car_unavailable,
  car_delay(district, minutes), bus_unavailable, member_no_trip(member), member_earlier_deadline(member, minutes)`).
  Incomplete answers are rejected and logged. Rules and the protocol then decide on the updated view. This engine was
  added after the first run showed the decision-making LLM *mentioning* the broken car in its reasons without changing its
  choices accordingly. Its vocabulary covers every effect the simulator can produce, so the comparison is a best case for
  it: a news item outside the vocabulary can only map to `none`.
- **Hybrid**: rule mode by default. It escalates to the LLM for the whole episode when a gate fires: free-text news
  outside the rule vocabulary is present, or the routine option is already late in the planner's view. The gate
  deliberately cannot judge relevance, so decoys trigger it; that cost is reported.

## 6. Communication protocol (communication ON)

Performatives: `inform, request, propose, counter, accept, reject, commit`.

1. The environment sends `inform` with the news. Children who must be accompanied send `request` to the household.
2. All agents send `propose` with their initial plans at the same time (nobody sees the others' plans yet).
3. Shared-blackboard conflict detection (deterministic): car over-claim, child with no companion, child with two
   companions.
4. **Car conflict:** every claimant sends `counter` with its declared concession cost (what giving up the car costs
   it, computed by its own planner). Each claimant then answers `reject` (keep) or `accept` (concede, with a new
   option). The rule engine concedes if its concession cost is among the lowest. The LLM engine decides freely.
   Up to 3 rounds. If the conflict is still open after that, it is a **deadlock**: an explicit, logged protocol
   tie-break applies (lowest concession cost gives way).
5. **Companion gap:** the child sends `request` to every possible companion, who answer `propose` or `reject`. The child
   `accept`s the cheapest offer. After 2 rounds with no offer, a logged tie-break applies.
6. **Duplicate companions:** the child keeps one companion and `reject`s the other, who re-plans.
7. Everyone sends `commit`. The committed joint plan is validated, and violations are counted, not repaired.

The LLM negotiates within a typed protocol (keep/concede, accept/decline + option ID). This is a deliberate choice:
outputs remain checkable and comparable across engines. It is not free-form dialogue.

## 7. Baselines

- **Central coordinator** (equal information): exhaustive search over joint plans that minimises simulated
  household cost under the *observed* view. No messages, no LLM. It is the strongest baseline: if communicating
  agents only reproduce it, the communication adds nothing beyond an algorithm.
- **Oracle** (upper bound, unattainable): the same search under the *ground truth*, which reads the text-only
  effects directly. Regret = executed cost minus oracle cost.

## 8. Protocol and statistics

- Full factorial: 5 households x 8 events x 3 seeds (seed 0 = canonical; seeds 1-2 jitter times by +/-10 min and
  durations by +/-15%) = **120 paired instances**, each run under 10 conditions (4 engines x communication off/on,
  plus the 2 baselines).
- Paired design: every condition runs on the same instances. Reported: means, 95% bootstrap CIs over instances,
  paired differences with better/tie/worse counts.
- LLM: every raw output, latency and token count is stored in `results/runs.jsonl`. An on-disk cache makes reruns
  reproducible; cached calls keep their original latency and are flagged.
- Sensitivity: the same grid with **qwen3:4b** (thinking disabled) for the LLM conditions.
- **Interpreter prompt development and held-out test.** The interpreter prompt was revised once (an explicit
  "evidence" field and one worked example from an unrelated household) after it failed on the scenario sentences, which
  therefore serve as development items. The prompt was then frozen, and a held-out set was written: 3 paraphrases per
  event type per household plus 4 adversarial decoys that mention cars, schools or buses without affecting today's trips
  (`hmcoop/heldout.py`, 80 items). Held-out accuracy is the number to quote for the interpreter.
- **Text uptake** (diagnostic): for each text-only event, whether the committed plan is consistent with what the news
  implies (no more drivers than working cars, no car trip into the blocked district, nobody travelling to a cancelled
  activity, the member with the earlier deadline arriving on time).
- Temperature 0 means the LLM rows measure one deterministic policy per model, not the spread of possible
  generations. Repeated sampling at T>0 is listed as future work.

## 9. Known limitations

Synthetic, uncalibrated times and weights; the interpreter's vocabulary matches the simulator's effects exactly; the
held-out paraphrases were written by the same author as the scenarios; one morning per household; no memory or habit formation; two small local
models; a typed negotiation rather than free dialogue; a gate that cannot judge relevance; the author designed the
scenarios. None of the results speak to survey-level realism.
