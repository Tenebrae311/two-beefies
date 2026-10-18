# topic-plate-placement-directions

**Question:** What does the Britannica say about Plate Placement Directions, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=11.9, n_calls=5, n_vision_calls=0, n_cited=2, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Plate Placement Directions", "k": 10})` -> 10 hits
- `search_wikipedia({"query": "Plate Placement Directions", "k": 10})` -> 10 hits
- `read_britannica({"cite_id": "EB:419-0"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:419-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:9508-0"})` -> 1 hits

## Answer

**Answer**: The 6th edition Britannica (1820–1823) contains a short printer's list, "Plate Placement Directions," stating on which page each engraved plate of Vol. XV (plates CCCLXX–CCCCIV) should face. Wikipedia has no article on plate placement directions; its closest match is the general article on the Encyclopædia Britannica as a whole. The difference is mainly NO_COUNTERPART, with some LANGUAGE change (Roman numerals, "to face page" phrasing).

**Britannica**: 6th edition (1820–1823), Vol. XV, NIC–PAR: "DIRECTIONS FOR PLACING THE PLATES OF VOL. XV. PART I. Plate CCCLXX. to face page 38; CCCLXXI.–CCCLXXIV. 164; CCCLXXV.–CCCLXXXIX. 288. PART II. CCCXC. 410; CCCXCI. 452; CCCXCII.–CCCCII. 562; CCCCIII. 718; CCCCIV. 749." [EB:419-0]

**Wikipedia**: The counterpart match is the general article "Encyclopædia Britannica," which describes the work's publication since 1768, its Edinburgh origins in three volumes, expansion to 20 volumes by the fourth edition, and its move online — it says nothing about plate placement [WP:9508-0]. No Wikipedia article covers plate placement directions.

**What changed**:
- NO_COUNTERPART: Wikipedia has no dedicated article on plate placement directions; only a general encyclopedia article.
- LANGUAGE: Roman plate numerals and the phrase "to face page" are obsolete printer's instructions; modern Wikipedia uses contemporary descriptive language.

**Confidence**: high on the Britannica text itself; medium on the comparison, since the Wikipedia counterpart is a general article rather than a matching subject.

## Citations

- `EB:419-0` (britannica) Plate Placement Directions: DIRECTIONS FOR PLACING THE PLATES OF VOL. XV. PART I. Plate CCCLXX. to face page 38 CCCLXXI.—CCCLXXIV. 164 CCCLXXV.—CCCLXXXIX. 288 PART II. CCCXC. 410 CCCXCI. 4
- `WP:9508-0` (wikipedia) Encyclopædia Britannica: The Encyclopædia Britannica (Latin for 'British Encyclopædia') is a general-knowledge English-language encyclopaedia. It has been published since 1768 and, afte

**Unsupported citation ids:** none

