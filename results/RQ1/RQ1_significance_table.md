# RQ1 Coverage Significance & Effect Sizes (All Baselines)

- **Test**: Wilcoxon signed-rank (paired per app)
- **Effect sizes**:
  - **Cohen's d** (paired): mean(Δ)/SD(Δ); |d|<0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, ≥0.8 large
  - **Rank-biserial r**: Wilcoxon-aligned effect; |r|<0.1 negligible, 0.1–0.3 small, 0.3–0.5 medium, ≥0.5 large
  - **Cliff's δ** (paired): (n₊−n₋)/n
- **Mapping**: `Monkey*-LLM`→HybridMonkey, `HybirdDroid`→HybridDroid

## HybridDroid — p-values

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | <0.001*** | <0.001*** | <0.001*** | <0.001*** |
| Monkey* | 0.6631 | 0.3013 | 0.2036 | 0.3394 |
| Fastbot | 0.0210* | 0.0425* | 0.0161* | 0.0093** |
| Droidbot* | 0.0024** | 0.0034** | 0.0015** | <0.001*** |
| GPTDroid | <0.001*** | <0.001*** | <0.001*** | <0.001*** |
| Aurora | <0.001*** | <0.001*** | <0.001*** | <0.001*** |

## HybridDroid — Cohen's d (paired)

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | 1.24 (large) | 1.048 (large) | 1.312 (large) | 1.339 (large) |
| Monkey* | 0.502 (medium) | 0.491 (small) | 0.549 (medium) | 0.49 (small) |
| Fastbot | 0.735 (medium) | 0.605 (medium) | 0.749 (medium) | 0.776 (medium) |
| Droidbot* | 0.944 (large) | 0.874 (large) | 0.986 (large) | 0.947 (large) |
| GPTDroid | 2.009 (large) | 1.793 (large) | 2.074 (large) | 1.948 (large) |
| Aurora | 1.436 (large) | 1.277 (large) | 1.487 (large) | 1.342 (large) |

## HybridDroid — Rank-biserial r

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |
| Monkey* | 0.154 (small) | 0.359 (medium) | 0.436 (medium) | 0.333 (medium) |
| Fastbot | 0.744 (large) | 0.667 (large) | 0.769 (large) | 0.821 (large) |
| Droidbot* | 0.923 (large) | 0.897 (large) | 0.949 (large) | 0.974 (large) |
| GPTDroid | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |
| Aurora | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |

## HybridMonkey — p-values

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | <0.001*** | <0.001*** | <0.001*** | <0.001*** |
| Monkey* | <0.001*** | <0.001*** | <0.001*** | 0.0068** |
| Fastbot | 0.0015** | 0.0161* | 0.0024** | <0.001*** |
| Droidbot* | <0.001*** | <0.001*** | <0.001*** | <0.001*** |
| GPTDroid | <0.001*** | <0.001*** | <0.001*** | <0.001*** |
| Aurora | <0.001*** | <0.001*** | <0.001*** | <0.001*** |

## HybridMonkey — Cohen's d (paired)

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | 1.563 (large) | 1.475 (large) | 1.465 (large) | 1.507 (large) |
| Monkey* | 0.82 (large) | 0.856 (large) | 0.835 (large) | 0.777 (medium) |
| Fastbot | 0.811 (large) | 0.77 (medium) | 0.785 (medium) | 0.813 (large) |
| Droidbot* | 1.252 (large) | 1.217 (large) | 1.215 (large) | 1.247 (large) |
| GPTDroid | 2.249 (large) | 2.075 (large) | 2.162 (large) | 2.101 (large) |
| Aurora | 1.639 (large) | 1.573 (large) | 1.609 (large) | 1.495 (large) |

## HybridMonkey — Rank-biserial r

| Baseline | Line | Branch | Method | Class |
|----------|------|--------|--------|-------|
| Monkey | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |
| Monkey* | 1.0 (large) | 1.0 (large) | 1.0 (large) | 0.846 (large) |
| Fastbot | 0.949 (large) | 0.769 (large) | 0.923 (large) | 1.0 (large) |
| Droidbot* | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |
| GPTDroid | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |
| Aurora | 1.0 (large) | 1.0 (large) | 1.0 (large) | 1.0 (large) |

