# sim_k Ablation — Line Coverage Summary

Source: `HybirdDroid实验记录 - ablation_simk.csv` (per-app values are averages over runs).

## k=8 vs other k per app

- Apps with k=8 data: **12** / 12
- k=8 is **unique** best line coverage: **9** apps
- k=8 is **tied** for best (includes unique): **9** apps
- k=8 is **not** among best: **3** apps

Among apps with **all k∈{5,6,7,8,9,10}** present (10 apps): k=8 unique best = **8**, k=8 tied-or-best = **8**.

> k=9 missing Chess & Feeder (API failures). Mean row uses available apps per k.

## Line coverage pivot (%)

| App | k=5 | k=6 | k=7 | k=8 | k=9 | k=10 | Best k |
|-----|------|------|------|------|------|------|--------|
| AlarmClock | 78.08 | 78.32 | 77.46 | 79.52 | 77.89 | 78.66 | 8 |
| AmazeFileManager | 29.10 | 30.71 | 31.23 | 36.50 | 33.20 | 33.60 | 8 |
| AnkiDroid | 27.40 | 28.37 | 28.01 | 40.14 | 33.42 | 34.59 | 8 |
| AntennaPod | 35.98 | 44.28 | 40.72 | 49.72 | 47.90 | 48.83 | 8 |
| Chess | 36.54 | 37.33 | 33.98 | 34.16 | — | 44.41 | 10 |
| Feeder | 9.79 | 10.96 | 11.71 | 46.83 | — | 13.59 | 8 |
| MyExpenses | 29.22 | 30.30 | 29.19 | 32.71 | 26.20 | 23.61 | 8 |
| NewPipe | 41.55 | 34.48 | 16.24 | 46.29 | 24.66 | 39.71 | 8 |
| Omni-Notes | 32.89 | 33.04 | 29.13 | 39.34 | 35.19 | 40.06 | 10 |
| OwnTracks | 55.76 | 58.08 | 55.89 | 62.04 | 57.62 | 55.24 | 8 |
| RedReader | 22.88 | 24.20 | 23.79 | 25.15 | 24.56 | 24.44 | 8 |
| Wikipedia | 13.83 | 15.25 | 12.82 | 14.86 | 13.86 | 13.49 | 6 |

## Apps where k=8 is not the best

| App | k=8 | Best k(s) | Max |
|-----|-----|-----------|-----|
| Chess | 34.160 | 10 | 44.414 |
| Omni-Notes | 39.340 | 10 | 40.060 |
| Wikipedia | 14.860 | 6 | 15.250 |
