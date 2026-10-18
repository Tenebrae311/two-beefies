# Ablation: scan resolution vs. VLM OCR

Model `nvidia/Nemotron-3.5-Super-VL` (thinking off), 8 pages. The dataset scans are 600 px wide; '1500 px' upscales them (LANCZOS) before sending.

**Generation loops: 6/8 pages at 600 px vs 0/8 at 1500 px.** 'chars' is the usable text after cutting loops; raw length in brackets.

| page | edition | 600 px: chars (raw) / loop | 1500 px: chars (raw) / loop |
|---|---|---|---|
| 26 Optical Instruments | 5th (1815-1817) | 3462 (7896) / LOOP | 4685 (4685) / ok |
| 102 Turkey: Geography and People | 7th (1830-1842) | 1590 (8859) / LOOP | 7869 (7869) / ok |
| 108 Rock Crystal Properties and Classification | 4th (1801-1810) | 1991 (16733) / LOOP | 6690 (6690) / ok |
| 122 Economists on Majority Rule | 4th-6th suppl. (1815-1824) | 3837 (18597) / LOOP | 6553 (6553) / ok |
| 130 Hydraulic Resistance Experiments | 3rd (1788-1797) | 1685 (17729) / LOOP | 6719 (6719) / ok |
| 356 Catechism and Catechumens | 3rd (1788-1797) | 15716 (15716) / ok | 6426 (6426) / ok |
| 383 Political Economy: Sources of Wealth | 5th (1815-1817) | 4270 (14989) / LOOP | 6446 (6446) / ok |
| 419 Plate Placement Directions | 6th (1820-1823) | 213 (213) / ok | 212 (212) / ok |
