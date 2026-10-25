# Experiment summary

Paired instances: **120** (household x event x seed), model: `qwen2.5:3b`, client config: `{'model': 'qwen2.5:3b', 'temperature': 0.0, 'seed': 7, 'constrained_decoding': True}`.

Regret = executed household generalized cost minus the oracle's (minutes-equivalent; lower is better). CI = 95% bootstrap over instances.

| condition | regret (CI95) | on-time | missed | intent conflicts | committed violations | exec failures | msgs | deadlocks | LLM calls | invalid | fallbacks | tokens | LLM s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rule-off | 76.6 (55.9, 98.8) | 82% | 6% | 0.28 | 0.28 | 0.56 | 0.9 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| rule-on | 34.1 (22.3, 47.4) | 86% | 3% | 0.28 | 0.0 | 0.25 | 7.7 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| llm-off | 128.3 (106.2, 151.9) | 70% | 21% | 0.63 | 0.63 | 0.78 | 0.9 | 0 | 2.4 | 0 | 0 | 1246 | 2.02 |
| llm-on | 89.6 (68.4, 112.1) | 76% | 15% | 0.64 | 0.0 | 0.21 | 10.1 | 9 | 3.9 | 0 | 13 | 2176 | 3.35 |
| hybrid-off | 110.3 (87.1, 135.2) | 74% | 15% | 0.48 | 0.48 | 0.64 | 0.9 | 0 | 1.55 | 0 | 0 | 836 | 1.35 |
| hybrid-on | 64.0 (47.0, 82.2) | 79% | 12% | 0.51 | 0.0 | 0.21 | 9.1 | 5 | 2.43 | 0 | 5 | 1411 | 2.14 |
| central | 33.8 (21.9, 47.0) | 86% | 4% | 0.0 | 0.0 | 0.25 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |
| oracle | 0.0 (0.0, 0.0) | 90% | 3% | 0.14 | 0.14 | 0.04 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0.0 |

## Regret by event kind

| condition | none | structured | unstructured | decoy |
|---|---|---|---|---|
| rule-off | 48.9 | 90.5 | 83.5 | 48.9 |
| rule-on | 0.0 | 1.5 | 67.5 | 0.0 |
| llm-off | 86.3 | 168.6 | 130.2 | 82.4 |
| llm-on | 36.1 | 103.6 | 110.3 | 32.0 |
| hybrid-off | 48.9 | 115.2 | 130.2 | 82.4 |
| hybrid-on | 0.0 | 19.3 | 110.3 | 32.0 |
| central | 0.0 | 0.0 | 67.5 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 |

## Regret by event

| condition | none | bus_strike | heavy_rain | car_breakdown | ringroad_accident | no_trip | deadline_change | decoy |
|---|---|---|---|---|---|---|---|---|
| rule-off | 48.9 | 112.7 | 68.4 | 81.9 | 147.3 | 34.3 | 70.6 | 48.9 |
| rule-on | 0.0 | 2.3 | 0.7 | 76.5 | 148.5 | 24.2 | 20.9 | 0.0 |
| llm-off | 86.3 | 150.6 | 186.6 | 137.5 | 178.6 | 64.9 | 139.9 | 82.4 |
| llm-on | 36.1 | 73.5 | 133.8 | 101.7 | 139.9 | 83.9 | 115.7 | 32.0 |
| hybrid-off | 48.9 | 112.7 | 117.8 | 137.5 | 178.6 | 64.9 | 139.9 | 82.4 |
| hybrid-on | 0.0 | 2.3 | 36.2 | 101.7 | 139.9 | 83.9 | 115.7 | 32.0 |
| central | 0.0 | 0.0 | 0.0 | 76.5 | 148.5 | 24.2 | 20.9 | 0.0 |
| oracle | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Paired comparisons (A minus B regret; negative = A better)

| comparison | mean diff (CI95) | A better / tie / worse | unstructured events only |
|---|---|---|---|
| rule-on vs rule-off | -42.5 (-64.2, -24.2) | 32 / 86 / 2 | -16.0 (-30.1, -4.0), n=60 |
| llm-on vs llm-off | -38.8 (-62.6, -15.0) | 68 / 25 / 27 | -19.9 (-38.0, -3.7), n=60 |
| hybrid-on vs hybrid-off | -46.4 (-67.2, -27.0) | 54 / 48 / 18 | -19.9 (-38.0, -3.7), n=60 |
| llm-on vs rule-on | 55.4 (36.3, 77.2) | 8 / 44 / 68 | 42.7 (22.4, 63.7), n=60 |
| hybrid-on vs rule-on | 29.8 (18.2, 43.4) | 8 / 68 / 44 | 42.7 (22.4, 63.7), n=60 |
| hybrid-on vs llm-on | -25.6 (-42.7, -12.0) | 28 / 91 / 1 | 0.0 (0.0, 0.0), n=60 |
| hybrid-off vs rule-off | 33.7 (21.1, 46.6) | 8 / 56 / 56 | 46.7 (28.9, 65.4), n=60 |
| rule-on vs central | 0.4 (0.0, 1.1) | 0 / 118 / 2 | 0.0 (0.0, 0.0), n=60 |
| llm-on vs central | 55.8 (36.6, 77.8) | 8 / 43 / 69 | 42.7 (22.4, 63.7), n=60 |
| hybrid-on vs central | 30.2 (18.5, 43.8) | 8 / 67 / 45 | 42.7 (22.4, 63.7), n=60 |

## Negative control: irrelevant news (decoy vs ordinary day)

| condition | agents whose plan changed | mean cost delta |
|---|---|---|
| rule-off | 0/36 | 0.0 |
| rule-on | 0/36 | 0.0 |
| llm-off | 2/36 | -3.9 |
| llm-on | 11/36 | -4.1 |
| hybrid-off | 12/36 | 33.5 |
| hybrid-on | 8/36 | 32.0 |
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
