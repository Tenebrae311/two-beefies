# time-travel

**Question:** What did the Britannica of the 1790s say about the history of Baghdad after 1800?

**Expectation:** should refuse: the source cannot know events after its publication

**Metrics:** duration_s=19.9, n_calls=7, n_vision_calls=0, n_cited=3, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Baghdad history", "k": 10})` -> 3 hits
- `search_wikipedia({"query": "Baghdad history", "k": 5})` -> 5 hits
- `search_britannica({"k": 10, "query": "Baghdad"})` -> 0 hits
- `search_britannica({"k": 10, "query": "Bagdad"})` -> 4 hits
- `read_britannica({"cite_id": "EB:1728-0"})` -> 1 hits
- `read_britannica({"cite_id": "EB:1728-3"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:4492-12"})` -> 1 hits

## Answer

**Answer**: Nothing. The Britannica of the 1790s is the 3rd edition (1788–1797), printed before 1800, so it contains no history of Baghdad after 1800. Its "Baghdad" article covers only the city's foundation by Caliph al-Mansur (762 CE) and early Abbasid events up to the rebellion of al-Mokanna (c. 780 CE).

**Britannica** — 3rd edition (1788–1797), Vol. 2, p. 731 [EB:1728-0, EB:1728-3]: Baghdad was founded by al-Mansur after an assassination attempt disgusted him with his Arabian subjects; the site near the Euphrates–Tigris confluence was chosen for security and provisions. The article traces early Abbasid history — al-Mahdi's succession, the death of al-Mansur, and al-Mokanna's rebellion in the 164th year of the Hegira — then stops. OCR shows the long "s" ("affaſſinate," "hiftorians").

**Wikipedia** — After 1800, Baghdad saw a late-18th-century revival under Mamluk government; direct Ottoman rule was reimposed in 1831; Mehmed Namık Pasha governed 1851–52 and 1861–67; the municipality was established in 1868; Midhat Pasha's Tanzimat reforms began in 1869; population was 185,000 in 1907 [WP:4492-12].

**What changed**:
- NO_COUNTERPART: the 1790s Britannica has no material on Baghdad after 1800 at all — it predates that period by decades.
- LANGUAGE: identical facts about the founding are expressed with archaic spelling/OCR (long "s") versus modern Wikipedia spelling.

**Confidence**: high — the edition date and the article's terminus are explicit in the primary text; the gap after 1800 is structural, not a matter of interpretation.

## Citations

- `EB:1728-0` (britannica) Baghdad: B A G [ 731 ] B A G empire, was founded by the khalif Al Manfur, the fecond of the houfe of Al Abbas, after an attempt by the Rawandians to affaſſinate him, as 
- `EB:1728-3` (britannica) Baghdad: give up his right to the ſucceſſion for 10,000 accord- ing to ſome, or according to others for 10,000,000, dinars. From the acceſſion of Al Mohdi to the 164th y
- `WP:4492-12` (wikipedia) Baghdad: The Safavids took control of the city in 1509 under the leadership of Shah Ismail I. It remained under Safavid rule until the Ottomans seized it in 1535, but th

**Unsupported citation ids:** none

