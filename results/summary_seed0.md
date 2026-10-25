# Experiment summary

Paired instances: **40** (household x event x seed), model: `qwen2.5:3b`, client config: `{'model': 'qwen2.5:3b', 'temperature': 0.0, 'seed': 7, 'constrained_decoding': True, 'think': None}`.

Regret = executed household generalized cost minus the oracle's (minutes-equivalent; lower is better). CI = 95% bootstrap over instances.

| condition | regret (CI95) | on-time | missed | intent conflicts | committed violations | exec failures | msgs | deadlocks | LLM calls | invalid | fallbacks | tokens | LLM s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rule-off | 62.3 (35.6, 96.8) | 82% | 3% | 0.4 | 0.4 | 0.68 | 0.9 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| rule-on | 19.8 (9.4, 32.6) | 91% | 2% | 0.4 | 0.0 | 0.25 | 8.1 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| llm-off | 148.9 (107.9, 200.1) | 72% | 20% | 0.6 | 0.6 | 0.72 | 0.9 | 0 | 2.4 | 0 | 0 | 1242 | 2.02 |
| llm-on | 56.6 (34.7, 83.2) | 80% | 10% | 0.6 | 0.0 | 0.2 | 9.8 | 3 | 3.73 | 0 | 2 | 2061 | 3.19 |
| hybrid-off | 107.5 (69.4, 152.6) | 77% | 12% | 0.45 | 0.45 | 0.57 | 0.9 | 0 | 1.52 | 0 | 0 | 819 | 1.34 |
| hybrid-on | 36.3 (20.8, 54.5) | 84% | 7% | 0.53 | 0.0 | 0.2 | 9.3 | 2 | 2.45 | 0 | 0 | 1411 | 2.16 |
| interp-off | 42.9 (16.9, 78.2) | 88% | 2% | 0.3 | 0.3 | 0.33 | 0.9 | 0 | 0.62 | 0 | 0 | 323 | 0.48 |
| interp-on | 1.5 (0.2, 3.5) | 94% | 0% | 0.3 | 0.0 | 0.0 | 7.6 | 0 | 0.62 | 0 | 0 | 323 | 0.48 |
| central | 19.8 (9.4, 32.6) | 91% | 2% | 0.0 | 0.0 | 0.25 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| oracle | 0.0 (0.0, 0.0) | 94% | 2% | 0.1 | 0.1 | 0.0 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |

## Regret by event kind

| condition | none | structured | unstructured | decoy |
|---|---|---|---|---|
| rule-off | 38.4 | 92.5 | 59.2 | 38.4 |
| rule-on | 0.0 | 0.0 | 39.5 | 0.0 |
| llm-off | 113.2 | 252.8 | 114.7 | 113.2 |
| llm-on | 82.4 | 64.2 | 55.3 | 20.6 |
| hybrid-off | 38.4 | 124.9 | 114.7 | 113.2 |
| hybrid-on | 0.0 | 24.5 | 55.3 | 20.6 |
| interp-off | 38.4 | 92.5 | 20.3 | 38.4 |
| interp-on | 0.0 | 0.0 | 3.0 | 0.0 |
| central | 0.0 | 0.0 | 39.5 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 |

## Regret by event

| condition | none | bus_strike | heavy_rain | car_breakdown | ringroad_accident | no_trip | deadline_change | decoy |
|---|---|---|---|---|---|---|---|---|
| rule-off | 38.4 | 113.4 | 71.7 | 50.5 | 82.1 | 35.6 | 68.5 | 38.4 |
| rule-on | 0.0 | 0.0 | 0.0 | 46.5 | 84.1 | 19.3 | 8.1 | 0.0 |
| llm-off | 113.2 | 262.6 | 243.0 | 131.4 | 148.0 | 52.3 | 127.2 | 113.2 |
| llm-on | 82.4 | 60.2 | 68.2 | 13.7 | 72.1 | 63.3 | 72.0 | 20.6 |
| hybrid-off | 38.4 | 113.4 | 136.3 | 131.4 | 148.0 | 52.3 | 127.2 | 113.2 |
| hybrid-on | 0.0 | 0.0 | 49.0 | 13.7 | 72.1 | 63.3 | 72.0 | 20.6 |
| interp-off | 38.4 | 113.4 | 71.7 | 4.5 | 2.0 | 6.0 | 68.5 | 38.4 |
| interp-on | 0.0 | 0.0 | 0.0 | 2.0 | 2.0 | 0.0 | 8.1 | 0.0 |
| central | 0.0 | 0.0 | 0.0 | 46.5 | 84.1 | 19.3 | 8.1 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired comparisons (A minus B regret; negative = A better)

| comparison | mean diff (CI95) | A better / tie / worse | unstructured events only |
|---|---|---|---|
| rule-on vs rule-off | -42.6 (-80.1, -15.2) | 15 / 24 / 1 | -19.7 (-46.0, 3.0), n=20 |
| llm-on vs llm-off | -92.3 (-135.3, -50.1) | 26 / 6 / 8 | -59.5 (-100.2, -18.8), n=20 |
| hybrid-on vs hybrid-off | -71.2 (-112.7, -37.8) | 21 / 14 / 5 | -59.5 (-100.2, -18.8), n=20 |
| llm-on vs rule-on | 36.8 (12.2, 65.6) | 4 / 14 / 22 | 15.7 (-14.9, 43.2), n=20 |
| hybrid-on vs rule-on | 16.6 (-0.6, 36.2) | 4 / 23 / 13 | 15.7 (-14.9, 43.2), n=20 |
| hybrid-on vs llm-on | -20.2 (-40.9, -5.2) | 10 / 30 / 0 | 0.0 (0.0, 0.0), n=20 |
| hybrid-off vs rule-off | 45.2 (15.3, 78.3) | 5 / 17 / 18 | 55.5 (14.8, 96.5), n=20 |
| interp-on vs rule-on | -18.2 (-31.2, -7.7) | 14 / 26 / 0 | -36.5 (-58.4, -16.6), n=20 |
| interp-on vs hybrid-on | -34.8 (-52.9, -19.2) | 22 / 18 / 0 | -52.2 (-73.2, -31.9), n=20 |
| interp-off vs rule-off | -19.5 (-31.9, -8.7) | 14 / 26 / 0 | -38.9 (-60.7, -19.5), n=20 |
| rule-on vs central | 0.0 (0.0, 0.0) | 0 / 40 / 0 | 0.0 (0.0, 0.0), n=20 |
| llm-on vs central | 36.8 (12.2, 65.6) | 4 / 14 / 22 | 15.7 (-14.9, 43.2), n=20 |
| interp-on vs central | -18.2 (-31.2, -7.7) | 14 / 26 / 0 | -36.5 (-58.4, -16.6), n=20 |

## Negative control: irrelevant news (decoy vs ordinary day)

| condition | agents whose plan changed | mean cost delta |
|---|---|---|
| rule-off | 0/12 | 0.0 |
| rule-on | 0/12 | 0.0 |
| llm-off | 0/12 | 0.0 |
| llm-on | 5/12 | -61.8 |
| hybrid-off | 5/12 | 74.8 |
| hybrid-on | 3/12 | 20.6 |
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
    "llm_calls_total": 98,
    "llm-on_calls_total": 149,
    "escalations_on_ordinary_or_structured_days": 1
  }
}
```

## Text uptake: committed plan consistent with the text-only news

| condition | car_breakdown | deadline_change | no_trip | ringroad_accident |
|---|---|---|---|---|
| rule-off | 0/5 | 2/5 | 0/5 | 0/5 |
| rule-on | 0/5 | 2/5 | 0/5 | 1/5 |
| llm-off | 3/5 | 1/5 | 2/5 | 1/5 |
| llm-on | 1/5 | 2/5 | 1/5 | 1/5 |
| hybrid-off | 3/5 | 1/5 | 2/5 | 1/5 |
| hybrid-on | 1/5 | 2/5 | 1/5 | 1/5 |
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
