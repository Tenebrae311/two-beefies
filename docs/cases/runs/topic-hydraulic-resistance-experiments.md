# topic-hydraulic-resistance-experiments

**Question:** What does the Britannica say about Hydraulic Resistance Experiments, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=20.3, n_calls=9, n_vision_calls=0, n_cited=5, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Hydraulic Resistance Experiments", "k": 10})` -> 10 hits
- `search_wikipedia({"query": "Hydraulic Resistance Experiments", "k": 10})` -> 10 hits
- `read_britannica({"cite_id": "EB:130-3"})` -> 1 hits
- `read_britannica({"cite_id": "EB:130-0"})` -> 1 hits
- `read_britannica({"cite_id": "EB:130-1"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:130-3"})` -> 2 hits
- `search_wikipedia({"k": 10, "query": "hydraulic resistance experiments De Buat coefficient friction pipes open channels"})` -> 10 hits
- `read_wikipedia({"cite_id": "WP:65424-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:11034-0"})` -> 1 hits

## Answer

**Answer:** Britannica's 3rd edition (1788–1797) treats "Hydraulic Resistance Experiments" as a first-person report of tests validating De Buat's rule for resistance in pipes and channels, including a syphon occlusion trial and a cylinder-vortex experiment [EB:130-0][EB:130-1][EB:130-3]. Wikipedia has no article by that name; its precomputed counterparts are the general articles "Hydraulics" and "Fluid dynamics" [WP:65424-0][WP:11034-0].

**Britannica:** 3rd edition (1788–1797, Vol. 16). The article repeats an experiment on occlusion of water in syphons and finds no sensible difference in filling time whether the syphon is horizontal or vertical, even with pressure over six times greater and added obstructions [EB:130-0]. It endorses De Buat's view that resistance depends on the relation between a section and its border, and that subtracting a constant (one-tenth inch) from √d makes √mg/(√d − 0.1) nearly constant (297 to 287 from small pipe to little canal, never below 256 in large canals and rivers) [EB:130-1]. A note describes whirling a polished cylinder in water, as Newton suggested, to study vortices and pipe resistance [EB:130-3]. The OCR renders long s as "f."

**Wikipedia:** "Hydraulics" defines the field as an applied science of the mechanical properties and use of liquids, rooted in fluid mechanics, governing energy via pressurized liquids, covering pipe flow, dam design, and open-channel flow [WP:65424-0]. "Fluid dynamics" is a subdiscipline of fluid mechanics covering flow of liquids and gases, with aerodynamics and hydrodynamics, applied to aircraft, pipelines, weather, nebulae, and geophysical flows, built on empirical and semi-empirical laws [WP:11034-0].

**What changed:**
- LANGUAGE: 18th-century OCR with long s ("ſ" → "f"), archaic spellings ("veſſels," "ſyphon"), first-person voice, vs. modern technical prose [EB:130-0][EB:130-1][EB:130-3] vs. [WP:65424-0][WP:11034-0].
- KNOWLEDGE: Britannica gives De Buat's specific experiments and numerical coefficient; Wikipedia covers the broad modern discipline and omits De Buat's experiments entirely [EB:130-0][EB:130-1] vs. [WP:65424-0][WP:11034-0].
- PERSPECTIVE: An individual experimenter verifying one engineer's rule vs. an impersonal survey of a whole field [EB:130-3] vs. [WP:65424-0][WP:11034-0].
- NO_COUNTERPART: No dedicated Wikipedia article on hydraulic resistance exists; the match is topical only.

**Confidence:** Medium. Britannica is legible despite long-s OCR, and counterparts are identified, but there is no direct Wikipedia equivalent, so the comparison is against general hydraulics/fluid dynamics articles.

## Citations

- `EB:130-0` (britannica) Hydraulic Resistance Experiments: 270 Theory. Obviated by an experiment on the occlusion of water in syphons. This might ſerve to juſtify our ingenious author; but he was determined to rely ever
- `EB:130-1` (britannica) Hydraulic Resistance Experiments: Thus Mr De Buat's opinion is completely juſtified; and he may be allowed to aſſert, that the refiſtance depends chiefly on the relation between the fection and 
- `EB:130-3` (britannica) Hydraulic Resistance Experiments: The writer of this article verified this by a very ſimple and inſtructive experiment. He was making experiments on the production of vortices, in the manner ſug
- `WP:65424-0` (wikipedia) Hydraulics: Hydraulics (from Ancient Greek ὕδωρ (húdōr) 'water' and αὐλός (aulós) 'pipe') is a technology and applied science using engineering, chemistry, and other scienc
- `WP:11034-0` (wikipedia) Fluid dynamics: In physics, physical chemistry, and engineering, fluid dynamics is a subdiscipline of fluid mechanics that describes the flow of fluids – liquids and gases. It 

**Unsupported citation ids:** none

