# Experiment summary

Paired instances: **40** (household x event x seed), model: `qwen3:4b`, client config: `{'model': 'qwen3:4b', 'temperature': 0.0, 'seed': 7, 'constrained_decoding': True, 'think': False}`.

Regret = executed household generalized cost minus the oracle's (minutes-equivalent; lower is better). CI = 95% bootstrap over instances.

| condition | regret (CI95) | on-time | missed | intent conflicts | committed violations | exec failures | msgs | deadlocks | LLM calls | invalid | fallbacks | tokens | LLM s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rule-off | 62.3 (35.6, 96.8) | 82% | 3% | 0.4 | 0.4 | 0.68 | 0.9 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| rule-on | 19.8 (9.4, 32.6) | 91% | 2% | 0.4 | 0.0 | 0.25 | 8.1 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| llm-off | 75.2 (42.9, 113.9) | 83% | 7% | 0.47 | 0.47 | 0.4 | 0.9 | 0 | 2.4 | 3 | 3 | 1288 | 5.17 |
| llm-on | 31.3 (19.9, 44.2) | 88% | 6% | 0.72 | 0.0 | 0.15 | 11.7 | 11 | 4.62 | 3 | 3 | 2808 | 9.02 |
| hybrid-off | 70.9 (39.5, 108.5) | 84% | 6% | 0.42 | 0.42 | 0.38 | 0.9 | 0 | 1.52 | 3 | 3 | 855 | 3.46 |
| hybrid-on | 28.8 (16.9, 42.2) | 88% | 6% | 0.55 | 0.0 | 0.15 | 9.7 | 5 | 2.62 | 3 | 3 | 1590 | 5.32 |
| interp-off | 42.9 (16.9, 78.2) | 88% | 2% | 0.3 | 0.3 | 0.33 | 0.9 | 0 | 0.62 | 0 | 0 | 333 | 1.31 |
| interp-on | 1.5 (0.2, 3.5) | 94% | 0% | 0.3 | 0.0 | 0.0 | 7.6 | 0 | 0.62 | 0 | 0 | 333 | 1.31 |
| central | 19.8 (9.4, 32.6) | 91% | 2% | 0.0 | 0.0 | 0.25 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| oracle | 0.0 (0.0, 0.0) | 94% | 2% | 0.1 | 0.1 | 0.0 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |

## Regret by event kind

| condition | none | structured | unstructured | decoy |
|---|---|---|---|---|
| rule-off | 38.4 | 92.5 | 59.2 | 38.4 |
| rule-on | 0.0 | 0.0 | 39.5 | 0.0 |
| llm-off | 6.1 | 125.9 | 80.3 | 22.3 |
| llm-on | 8.9 | 5.4 | 55.4 | 8.9 |
| hybrid-off | 38.4 | 92.5 | 80.3 | 22.3 |
| hybrid-on | 0.0 | 0.0 | 55.4 | 8.9 |
| interp-off | 38.4 | 92.5 | 20.3 | 38.4 |
| interp-on | 0.0 | 0.0 | 3.0 | 0.0 |
| central | 0.0 | 0.0 | 39.5 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 |

## Regret by event

| condition | none | bus_strike | heavy_rain | car_breakdown | ringroad_accident | no_trip | deadline_change | decoy |
|---|---|---|---|---|---|---|---|---|
| rule-off | 38.4 | 113.4 | 71.7 | 50.5 | 82.1 | 35.6 | 68.5 | 38.4 |
| rule-on | 0.0 | 0.0 | 0.0 | 46.5 | 84.1 | 19.3 | 8.1 | 0.0 |
| llm-off | 6.1 | 134.6 | 117.2 | 86.4 | 141.9 | 18.5 | 74.3 | 22.3 |
| llm-on | 8.9 | 5.6 | 5.1 | 41.4 | 87.1 | 59.5 | 33.7 | 8.9 |
| hybrid-off | 38.4 | 113.4 | 71.7 | 86.4 | 141.9 | 18.5 | 74.3 | 22.3 |
| hybrid-on | 0.0 | 0.0 | 0.0 | 41.4 | 87.1 | 59.5 | 33.7 | 8.9 |
| interp-off | 38.4 | 113.4 | 71.7 | 4.5 | 2.0 | 6.0 | 68.5 | 38.4 |
| interp-on | 0.0 | 0.0 | 0.0 | 2.0 | 2.0 | 0.0 | 8.1 | 0.0 |
| central | 0.0 | 0.0 | 0.0 | 46.5 | 84.1 | 19.3 | 8.1 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired comparisons (A minus B regret; negative = A better)

| comparison | mean diff (CI95) | A better / tie / worse | unstructured events only |
|---|---|---|---|
| rule-on vs rule-off | -42.6 (-80.1, -15.2) | 15 / 24 / 1 | -19.7 (-46.0, 3.0), n=20 |
| llm-on vs llm-off | -43.9 (-83.1, -12.2) | 18 / 15 / 7 | -24.8 (-65.4, 9.3), n=20 |
| hybrid-on vs hybrid-off | -42.0 (-79.5, -13.2) | 17 / 18 / 5 | -24.8 (-65.4, 9.3), n=20 |
| llm-on vs rule-on | 11.5 (5.0, 19.3) | 1 / 19 / 20 | 15.9 (3.3, 30.7), n=20 |
| hybrid-on vs rule-on | 9.1 (2.5, 17.1) | 1 / 27 / 12 | 15.9 (3.3, 30.7), n=20 |
| hybrid-on vs llm-on | -2.5 (-4.2, -1.0) | 8 / 32 / 0 | 0.0 (0.0, 0.0), n=20 |
| hybrid-off vs rule-off | 8.5 (-10.5, 29.7) | 9 / 20 / 11 | 21.1 (-8.8, 56.8), n=20 |
| interp-on vs rule-on | -18.2 (-31.2, -7.7) | 14 / 26 / 0 | -36.5 (-58.4, -16.6), n=20 |
| interp-on vs hybrid-on | -27.3 (-40.3, -15.7) | 20 / 20 / 0 | -52.4 (-73.5, -31.4), n=20 |
| interp-off vs rule-off | -19.5 (-31.9, -8.7) | 14 / 26 / 0 | -38.9 (-60.7, -19.5), n=20 |
| rule-on vs central | 0.0 (0.0, 0.0) | 0 / 40 / 0 | 0.0 (0.0, 0.0), n=20 |
| llm-on vs central | 11.5 (5.0, 19.3) | 1 / 19 / 20 | 15.9 (3.3, 30.7), n=20 |
| interp-on vs central | -18.2 (-31.2, -7.7) | 14 / 26 / 0 | -36.5 (-58.4, -16.6), n=20 |

## Negative control: irrelevant news (decoy vs ordinary day)

| condition | agents whose plan changed | mean cost delta |
|---|---|---|
| rule-off | 0/12 | 0.0 |
| rule-on | 0/12 | 0.0 |
| llm-off | 2/12 | 16.2 |
| llm-on | 0/12 | 0.0 |
| hybrid-off | 5/12 | -16.1 |
| hybrid-on | 3/12 | 8.9 |
| interp-off | 0/12 | 0.0 |
| interp-on | 0/12 | 0.0 |
| central | 0/12 | 0.0 |
| oracle | 0/12 | 0.0 |

## Hybrid gate

```json
{
  "hybrid-off": {
    "episodes_with_escalation": 26,
    "episodes": 40,
    "llm_calls_total": 61,
    "llm-off_calls_total": 96,
    "escalations_on_ordinary_or_structured_days": 1
  },
  "hybrid-on": {
    "episodes_with_escalation": 26,
    "episodes": 40,
    "llm_calls_total": 105,
    "llm-on_calls_total": 185,
    "escalations_on_ordinary_or_structured_days": 1
  }
}
```

## Text uptake: committed plan consistent with the text-only news

| condition | car_breakdown | deadline_change | no_trip | ringroad_accident |
|---|---|---|---|---|
| rule-off | 0/5 | 2/5 | 0/5 | 0/5 |
| rule-on | 0/5 | 2/5 | 0/5 | 1/5 |
| llm-off | 4/5 | 2/5 | 5/5 | 1/5 |
| llm-on | 3/5 | 1/5 | 1/5 | 1/5 |
| hybrid-off | 4/5 | 2/5 | 5/5 | 1/5 |
| hybrid-on | 3/5 | 1/5 | 1/5 | 1/5 |
| interp-off | 4/5 | 2/5 | 5/5 | 5/5 |
| interp-on | 5/5 | 2/5 | 5/5 | 5/5 |
| central | 0/5 | 2/5 | 0/5 | 1/5 |
| oracle | 5/5 | 2/5 | 5/5 | 5/5 |

## Interpreter accuracy (exact match with ground-truth effect)

```json
{
  "interp-off": {
    "car_breakdown": "5/5",
    "deadline_change": "5/5",
    "decoy": "5/5",
    "no_trip": "5/5",
    "ringroad_accident": "5/5"
  },
  "interp-on": {
    "car_breakdown": "5/5",
    "deadline_change": "5/5",
    "decoy": "5/5",
    "no_trip": "5/5",
    "ringroad_accident": "5/5"
  }
}
```
