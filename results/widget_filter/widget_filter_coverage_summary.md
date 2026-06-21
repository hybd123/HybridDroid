# Widget Filter Optimization — Coverage Comparison

Source: `HybridDroid实验(最新) - RQ1覆盖率数据（控件过滤优化）.csv`

- **Before**: coverage before widget-occlusion filtering fix
- **After**: coverage after optimization
- **Δ** = After − Before (negative ⇒ reported coverage decreases after fix)

## Overall average (12 apps)

| Metric | Before (%) | After (%) | Δ (After−Before) | Apps in After avg |
|--------|------------|-----------|------------------|-------------------|
| Line | 42.71 | 42.03 | -1.46* | 11/12 |
| Branch | 29.82 | 29.62 | -1.14* | 11/12 |
| Method | 46.39 | 44.72 | -1.13* | 11/12 |
| Class | 54.63 | 53.05 | -0.82* | 11/12 |

\* Δ mean uses **11 apps** with both Before and After (Feeder missing After).

## Per-app Line coverage

| App | Issues | Before | After | Δ |
|-----|--------|--------|-------|---|
| AlarmClock | 0 | 79.52 | 78.24 | -1.28 |
| AmazeFileManager | 4 | 36.50 | 34.68 | -1.82 |
| AnkiDroid | 7 | 40.14 | 39.85 | -0.29 |
| AntennaPod | 4 | 49.72 | 45.81 | -3.91 |
| Chess | 0 | 46.83 | 46.49 | -0.34 |
| Feeder | 0 | 34.16 | — | — |
| MyExpenses | 12 | 32.71 | 33.32 | +0.61 |
| NewPipe | 3 | 46.29 | 44.05 | -2.24 |
| Omni-Notes | 4 | 44.66 | 48.38 | +3.72 |
| OwnTracks | 1 | 62.04 | 53.77 | -8.27 |
| RedReader | 1 | 25.15 | 22.81 | -2.34 |
| Wikipedia | 1 | 14.86 | 14.95 | +0.09 |

**Line coverage**: After > Before on **3** apps; After < Before on **8** apps.
- Increased: MyExpenses, Omni-Notes, Wikipedia
- Decreased: AlarmClock, AmazeFileManager, AnkiDroid, AntennaPod, Chess, NewPipe, OwnTracks, RedReader
- Feeder: only Before data available (After missing).
