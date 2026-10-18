# topic-catechism-and-catechumens

**Question:** What does the Britannica say about Catechism and Catechumens, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=9.5, n_calls=5, n_vision_calls=0, n_cited=2, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Catechism and Catechumens", "k": 10})` -> 3 hits
- `search_wikipedia({"query": "Catechism and Catechumens", "k": 10})` -> 10 hits
- `read_britannica({"cite_id": "EB:356-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:295855-0"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:356-0"})` -> 2 hits

## Answer

**Answer** — Britannica's 3rd edition (1788–1797) defines catechism as oral, repetitious instruction in the principles of Christianity given to those preparing for baptism, and later an elementary question-and-answer book; modern Wikipedia describes a catechism as a doctrinal summary/manual introducing the sacraments, used across Christian traditions and secular contexts, with catechumens as those preparing for baptism. [EB:356-0][WP:295855-0]

**Britannica** — "Catechism and Catechumens," Encyclopaedia Britannica, 3rd edition (1788–1797), Vol. 4, p. 250. Catechesis is "infruction given viva voce" to children or adult heathens before baptism, distinct from higher "myſtagogica" for the initiated. Teachers are catechifts; pupils are catechumens, anciently in four orders (private instruction; audientes hearing sermons; genuflectentes; competentes & electi awaiting baptism). Catechism derives, per Britannica, from Greek κατηχέω (κατά + ἦχος, "circumsono," the "noise or din" of repetition); anciently taught without writing, like Egyptian priests and British/Gaulish druids; "in modern times" it means an elementary book of articles of religion in question and answer. Catechists were ministers under bishops, not a distinct clergy order. [EB:356-0]

**Wikipedia** — "Catechism": a summary or exposition of doctrine introducing the Sacraments, used in catechesis (Christian teaching of children and adult converts); Greek κατηχέω = "to teach orally"; attested in the New Testament for instructing believers. Usually Q&A manuals to memorize; the format is also secular. A catechumen is the recipient; in the Catholic Church, catechumens prepare for baptism and are dismissed before the Creed and intercessions. Catechisms are characteristic of Western Christianity but exist in Eastern Christianity; the 1973 Common Catechism was the first joint Catholic–Protestant catechism. [WP:295855-0]

**What changed**
- LANGUAGE: OCR archaica (long s read as "f": catechifs, infruction, baptifm); Britannica's etymology (κατά + ἦχος, "din") vs. Wikipedia's "to teach orally." [EB:356-0][WP:295855-0]
- KNOWLEDGE: Wikipedia adds New Testament usage, secular catechisms, Eastern Orthodoxy, and the 1973 ecumenical Common Catechism — post-1797 developments. Britannica's four orders of catechumens and druidic oral-tradition analogy are absent from the Wikipedia lead. [EB:356-0][WP:295855-0]
- PERSPECTIVE: Britannica assumes one establishment Christianity under bishops; Wikipedia is pluralist/ecumenical across Catholic, Protestant, Orthodox, and secular uses. [EB:356-0][WP:295855-0]

**Confidence** — high. Sources: Britannica 3rd ed. full page and Wikipedia Catechism lead, precomputed counterpart match confirmed. Missing: fuller Wikipedia Catechesis treatment of the ancient catechumen orders for a complete symmetry check.

## Citations

- `EB:356-0` (britannica) Catechism and Catechumens: C A T. [ 250 ] C A T Catechetic Catechu- men. frution given any perfom in the first rudiments of an art or science; but more particularly of the Chriſtian relig
- `WP:295855-0` (wikipedia) Catechism: A catechism ( ; from Ancient Greek: κατηχέω, "to teach orally") is a summary or exposition of doctrine and serves as a learning introduction to the Sacraments t

**Unsupported citation ids:** none

