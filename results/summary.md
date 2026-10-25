# Experiment summary

Paired instances: **120** (household x event x seed), model: `qwen2.5:3b`, client config: `{'model': 'qwen2.5:3b', 'temperature': 0.0, 'seed': 7, 'constrained_decoding': True, 'think': None}`.

Regret = executed household generalized cost minus the oracle's (minutes-equivalent; lower is better). CI = 95% bootstrap over instances.

| condition | regret (CI95) | on-time | missed | intent conflicts | committed violations | exec failures | msgs | deadlocks | LLM calls | invalid | fallbacks | tokens | LLM s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rule-off | 74.2 (52.8, 97.7) | 82% | 6% | 0.28 | 0.28 | 0.56 | 0.9 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| rule-on | 31.7 (20.0, 45.5) | 86% | 3% | 0.28 | 0.0 | 0.25 | 7.7 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| llm-off | 160.9 (137.4, 184.9) | 70% | 21% | 0.63 | 0.63 | 0.78 | 0.9 | 0 | 2.4 | 0 | 0 | 1246 | 2.02 |
| llm-on | 87.1 (65.9, 110.7) | 76% | 15% | 0.64 | 0.0 | 0.21 | 10.1 | 9 | 3.9 | 0 | 13 | 2176 | 3.35 |
| hybrid-off | 122.9 (99.3, 149.3) | 74% | 15% | 0.48 | 0.48 | 0.64 | 0.9 | 0 | 1.55 | 0 | 0 | 836 | 1.35 |
| hybrid-on | 61.5 (44.6, 79.6) | 79% | 12% | 0.51 | 0.0 | 0.21 | 9.1 | 5 | 2.43 | 0 | 5 | 1411 | 2.14 |
| interp-off | 49.0 (30.0, 70.4) | 86% | 5% | 0.24 | 0.24 | 0.27 | 0.9 | 0 | 0.62 | 0 | 0 | 322 | 0.53 |
| interp-on | 6.6 (2.6, 12.3) | 90% | 1% | 0.24 | 0.0 | 0.0 | 7.4 | 0 | 0.62 | 0 | 0 | 322 | 0.53 |
| central | 31.3 (19.3, 45.2) | 86% | 4% | 0.0 | 0.0 | 0.25 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| oracle | 0.0 (0.0, 0.0) | 90% | 2% | 0.12 | 0.12 | 0.03 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |

## Regret by event kind

| condition | none | structured | unstructured | decoy |
|---|---|---|---|---|
| rule-off | 48.9 | 90.5 | 78.7 | 48.9 |
| rule-on | 0.0 | 1.5 | 62.7 | 0.0 |
| llm-off | 126.3 | 228.6 | 147.9 | 112.4 |
| llm-on | 36.1 | 103.6 | 105.4 | 32.0 |
| hybrid-off | 48.9 | 115.2 | 147.9 | 112.4 |
| hybrid-on | 0.0 | 19.3 | 105.4 | 32.0 |
| interp-off | 48.9 | 90.5 | 28.3 | 48.9 |
| interp-on | 0.0 | 1.5 | 12.4 | 0.0 |
| central | 0.0 | 0.0 | 62.7 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 |

## Regret by event

| condition | none | bus_strike | heavy_rain | car_breakdown | ringroad_accident | no_trip | deadline_change | decoy |
|---|---|---|---|---|---|---|---|---|
| rule-off | 48.9 | 112.7 | 68.4 | 57.1 | 152.6 | 34.3 | 70.6 | 48.9 |
| rule-on | 0.0 | 2.3 | 0.7 | 51.8 | 153.8 | 24.2 | 20.9 | 0.0 |
| llm-off | 126.3 | 220.6 | 236.6 | 152.8 | 213.9 | 64.9 | 159.9 | 112.4 |
| llm-on | 36.1 | 73.5 | 133.8 | 77.0 | 145.2 | 83.9 | 115.7 | 32.0 |
| hybrid-off | 48.9 | 112.7 | 117.8 | 152.8 | 213.9 | 64.9 | 159.9 | 112.4 |
| hybrid-on | 0.0 | 2.3 | 36.2 | 77.0 | 145.2 | 83.9 | 115.7 | 32.0 |
| interp-off | 48.9 | 112.7 | 68.4 | 14.9 | 22.3 | 3.7 | 72.2 | 48.9 |
| interp-on | 0.0 | 2.3 | 0.7 | 9.5 | 20.6 | 0.0 | 19.4 | 0.0 |
| central | 0.0 | 0.0 | 0.0 | 51.8 | 153.8 | 24.2 | 20.9 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired comparisons (A minus B regret; negative = A better)

| comparison | mean diff (CI95) | A better / tie / worse | unstructured events only |
|---|---|---|---|
| rule-on vs rule-off | -42.5 (-64.2, -24.2) | 32 / 86 / 2 | -16.0 (-30.1, -4.0), n=60 |
| llm-on vs llm-off | -73.8 (-99.3, -45.3) | 70 / 25 / 25 | -42.4 (-66.9, -19.7), n=60 |
| hybrid-on vs hybrid-off | -61.4 (-83.6, -40.6) | 56 / 48 / 16 | -42.4 (-66.9, -19.7), n=60 |
| llm-on vs rule-on | 55.4 (36.3, 77.2) | 8 / 44 / 68 | 42.7 (22.4, 63.7), n=60 |
| hybrid-on vs rule-on | 29.8 (18.2, 43.4) | 8 / 68 / 44 | 42.7 (22.4, 63.7), n=60 |
| hybrid-on vs llm-on | -25.6 (-42.7, -12.0) | 28 / 91 / 1 | 0.0 (0.0, 0.0), n=60 |
| hybrid-off vs rule-off | 48.7 (32.9, 64.7) | 6 / 56 / 58 | 69.2 (46.3, 92.5), n=60 |
| interp-on vs rule-on | -25.1 (-38.1, -14.5) | 44 / 76 / 0 | -50.3 (-74.1, -30.4), n=60 |
| interp-on vs hybrid-on | -55.0 (-71.7, -39.0) | 68 / 52 / 0 | -93.0 (-119.2, -68.7), n=60 |
| interp-off vs rule-off | -25.2 (-38.2, -14.4) | 40 / 79 / 1 | -50.4 (-74.5, -29.7), n=60 |
| rule-on vs central | 0.4 (0.0, 1.1) | 0 / 118 / 2 | 0.0 (0.0, 0.0), n=60 |
| llm-on vs central | 55.8 (36.6, 77.8) | 8 / 43 / 69 | 42.7 (22.4, 63.7), n=60 |
| interp-on vs central | -24.8 (-37.9, -14.1) | 44 / 74 / 2 | -50.3 (-74.1, -30.4), n=60 |

## Negative control: irrelevant news (decoy vs ordinary day)

| condition | agents whose plan changed | mean cost delta |
|---|---|---|
| rule-off | 0/36 | 0.0 |
| rule-on | 0/36 | 0.0 |
| llm-off | 2/36 | -13.9 |
| llm-on | 11/36 | -4.1 |
| hybrid-off | 12/36 | 63.5 |
| hybrid-on | 8/36 | 32.0 |
| interp-off | 0/36 | 0.0 |
| interp-on | 0/36 | 0.0 |
| central | 0/36 | 0.0 |
| oracle | 0/36 | 0.0 |

## Hybrid gate

```json
{
  "hybrid-off": {
    "episodes_with_escalation": 80,
    "episodes": 120,
    "llm_calls_total": 186,
    "llm-off_calls_total": 288,
    "escalations_on_ordinary_or_structured_days": 5
  },
  "hybrid-on": {
    "episodes_with_escalation": 80,
    "episodes": 120,
    "llm_calls_total": 292,
    "llm-on_calls_total": 468,
    "escalations_on_ordinary_or_structured_days": 5
  }
}
```

## Text uptake: committed plan consistent with the text-only news

| condition | car_breakdown | deadline_change | no_trip | ringroad_accident |
|---|---|---|---|---|
| rule-off | 0/15 | 7/15 | 0/15 | 1/15 |
| rule-on | 0/15 | 7/15 | 0/15 | 2/15 |
| llm-off | 4/15 | 5/15 | 6/15 | 1/15 |
| llm-on | 3/15 | 6/15 | 2/15 | 4/15 |
| hybrid-off | 4/15 | 5/15 | 6/15 | 1/15 |
| hybrid-on | 3/15 | 6/15 | 2/15 | 4/15 |
| interp-off | 12/15 | 7/15 | 15/15 | 14/15 |
| interp-on | 15/15 | 7/15 | 15/15 | 15/15 |
| central | 0/15 | 7/15 | 0/15 | 2/15 |
| oracle | 15/15 | 8/15 | 15/15 | 15/15 |

## Interpreter accuracy (exact match with ground-truth effect)

```json
{
  "interp-off": {
    "car_breakdown": "15/15",
    "deadline_change": "15/15",
    "decoy": "15/15",
    "no_trip": "15/15",
    "ringroad_accident": "15/15"
  },
  "interp-on": {
    "car_breakdown": "15/15",
    "deadline_change": "15/15",
    "decoy": "15/15",
    "no_trip": "15/15",
    "ringroad_accident": "15/15"
  }
}
```
