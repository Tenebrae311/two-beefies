# Ablation: does retrieval find the page for its own topic?

Candidates: full-text (LanceDB FTS). Query = the page's title (as a user would phrase the topic). Cell = rank of the page among results (miss = not found).

- **candidates only**: hit@5 35/36, MRR 0.90

(No reranker configured - set NVIDIA_API_KEY or RERANK_URL to add the rerank column.)

| page | title (query) | candidates only |
|---|---|---|
| 26 | Optical Instruments | 3 |
| 102 | Turkey: Geography and People | 1 |
| 108 | Rock Crystal Properties and Classification | 1 |
| 122 | Economists on Majority Rule | 1 |
| 130 | Hydraulic Resistance Experiments | 1 |
| 289 | West Indies Map | 1 |
| 356 | Catechism and Catechumens | 1 |
| 360 | Giraffe | 1 |
| 383 | Political Economy: Sources of Wealth | 1 |
| 419 | Plate Placement Directions | 1 |
| 456 | Greenland | 2 |
| 571 | Surgery: Inflammation Treatment | 2 |
| 641 | Bridges and Viaducts | 1 |
| 653 | Coak and Coalery | 1 |
| 814 | Terrestrial Magnetism and Gauss | 1 |
| 895 | Lizards and Crocodiles | 1 |
| 902 | Greenland | 1 |
| 908 | Abacus and Acoustics | 1 |
| 914 | Arabia | 1 |
| 952 | London Wards and Buildings | 1 |
| 1003 | Atmospheric Electricity | 1 |
| 1029 | Plate CIII: Salamander, Hare, Rabbit, Logarithms, Lozenge, Lapidary's Mill | 1 |
| 1126 | Miniature-Painting: Flowers | 1 |
| 1139 | Bills of Mortality | 1 |
| 1718 | Ardebil, Arden | 1 |
| 1728 | Baghdad | miss |
| 1731 | Architecture: Hut Origins | 1 |
| 1839 | Brasil | 1 |
| 2069 | Britain 1795 War and Politics | 1 |
| 2232 | Algebra: Roots and Equations | 1 |
| 2233 | Architecture: Door Designs | 2 |
| 2243 | Astronomical Models and Eclipses | 1 |
| 2298 | Boleslaw's Polish Wars | 1 |
| 2413 | Algiers | 1 |
| 2418 | Algebra: Fractions and Powers | 1 |
| 2465 | Sundial Construction and Types | 2 |
