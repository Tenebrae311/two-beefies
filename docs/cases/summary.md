# Agent case runs

16 runs, model `nvidia/Nemotron-3.5-Super-VL`, generated 2026-10-18 14:28 UTC.

- citations backed by a retrieved source: 67/67 (100%)
- gold page retrieved (topic questions): 10/10
- mean reranker support of answer claims: n/a (no reranker)

| case | verdict | stage | s | calls | vision | cited | unsupported | support | gold page |
|---|---|---|---|---|---|---|---|---|---|
| [aggregate-count](runs/aggregate-count.md) | failure | Retrieval (architecture) | 16.5 | 5 | 0 | 8 | 0 | - | - |
| [ambiguity-mercury](runs/ambiguity-mercury.md) | failure | Retrieval -> Agent reasoning | 32.1 | 15 | 0 | 3 | 0 | - | - |
| [long-s](runs/long-s.md) | failure | Retrieval (FTS stop words) -> Agent reasoning | 11.8 | 5 | 0 | 7 | 0 | - | - |
| [modern-term](runs/modern-term.md) | success | Retrieval (recovered by the agent) | 17.4 | 11 | 0 | 3 | 0 | - | - |
| [not-indexed](runs/not-indexed.md) | - | - | 23.7 | 16 | 0 | 4 | 0 | - | - |
| [plate-giraffe](runs/plate-giraffe.md) | success | Agent reasoning (vision tools) | 32.5 | 8 | 2 | 2 | 0 | - | yes |
| [plate-west-indies-map](runs/plate-west-indies-map.md) | - | - | 28.5 | 4 | 2 | 2 | 0 | - | yes |
| [time-travel](runs/time-travel.md) | success | Agent reasoning | 19.9 | 7 | 0 | 3 | 0 | - | - |
| [topic-catechism-and-catechumens](runs/topic-catechism-and-catechumens.md) | - | - | 9.5 | 5 | 0 | 2 | 0 | - | yes |
| [topic-economists-on-majority-rule](runs/topic-economists-on-majority-rule.md) | - | - | 16.2 | 8 | 0 | 8 | 0 | - | yes |
| [topic-hydraulic-resistance-experiments](runs/topic-hydraulic-resistance-experiments.md) | - | - | 20.3 | 9 | 0 | 5 | 0 | - | yes |
| [topic-optical-instruments](runs/topic-optical-instruments.md) | - | - | 21.5 | 7 | 0 | 3 | 0 | - | yes |
| [topic-plate-placement-directions](runs/topic-plate-placement-directions.md) | - | - | 11.9 | 5 | 0 | 2 | 0 | - | yes |
| [topic-political-economy-sources-of-wealth](runs/topic-political-economy-sources-of-wealth.md) | - | - | 13.2 | 7 | 0 | 4 | 0 | - | yes |
| [topic-rock-crystal-properties-and-classification](runs/topic-rock-crystal-properties-and-classification.md) | - | - | 22.8 | 10 | 0 | 8 | 0 | - | yes |
| [topic-turkey-geography-and-people](runs/topic-turkey-geography-and-people.md) | - | - | 20.7 | 11 | 0 | 3 | 0 | - | yes |
