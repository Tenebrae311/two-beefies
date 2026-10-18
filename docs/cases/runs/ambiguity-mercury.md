# ambiguity-mercury

**Question:** What does each source say about Mercury?

**Expectation:** failure risk (Retrieval): ambiguous term - planet, god or metal

**Metrics:** duration_s=32.1, n_calls=15, n_vision_calls=0, n_cited=3, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Mercury", "k": 10})` -> 0 hits
- `search_wikipedia({"query": "Mercury", "k": 10})` -> 10 hits
- `search_britannica({"k": 10, "query": "Mercurius"})` -> 0 hits
- `search_britannica({"k": 10, "query": "quicksilver"})` -> 0 hits
- `search_wikipedia({"k": 5, "query": "Mercury (planet)"})` -> 5 hits
- `search_wikipedia({"k": 5, "query": "Mercury (element)"})` -> 5 hits
- `search_britannica({"k": 5, "query": "planet"})` -> 0 hits
- `search_britannica({"k": 5, "query": "Hermes"})` -> 0 hits
- `search_wikipedia({"k": 5, "query": "Mercury (mythology)"})` -> 5 hits
- `search_britannica({"k": 5, "query": "Sun"})` -> 1 hits
- `search_britannica({"k": 5, "query": "Mercury", "edition": "3rd"})` -> 0 hits
- `read_britannica({"cite_id": "EB:2243-1"})` -> 1 hits
- `search_britannica({"k": 5, "query": "Mercury planet"})` -> 0 hits
- `read_wikipedia({"cite_id": "WP:244588-19"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:244588-7"})` -> 1 hits

## Answer

**Answer** — Wikipedia treats Mercury primarily as a planet within historical astronomical models (Martianus Capella's and Tycho Brahe's systems) and secondarily as the element mercury used in pressure measurement; Britannica (editions 1–8, 1768–1860) has no indexed content on Mercury at all — searches for "Mercury," "Mercurius," "quicksilver," "Hermes," and even "planet" return nothing, although the search itself works (it returns results for "Sun").

**Britannica** — No passages found. Despite confirming the Britannica search is functional, it returns zero results for Mercury in any sense (planet, element, or god) across editions 1–8 (1768–1860). [No citation id available — empty result set.]

**Wikipedia** — Mercury appears as a planet in historical cosmology: Martianus Capella (5th c. CE, Roman Carthage) held that Venus and Mercury circle the Sun rather than Earth, a model Copernicus later cited as an influence [WP:244588-7]; Tycho Brahe's Tychonic system (c. 1587) placed Mercury and Venus orbiting the Sun inside the Sun's orbit of Earth, while the Sun and Moon orbit Earth [WP:244588-19]. The element mercury also appears as a pressure-measurement medium ("mercury column") in fluid dynamics [WP:11034-20]. No standalone Mercury article surfaced in this snapshot.

**What changed**
- NO_COUNTERPART: Britannica has no material on Mercury; Wikipedia has extensive astronomical treatment of the planet and passing treatment of the element.

**Confidence** — Medium. Wikipedia evidence is direct and cited. The Britannica null result is reliable (search verified working), but I cannot rule out that Mercury appears in OCR-garbled form not matched by modern spelling; no edition-specific Mercury passage was located.

## Citations

- `WP:244588-7` (wikipedia) Heliocentrism: There were occasional speculations about heliocentrism in Europe before Copernicus. In Roman Carthage, the pagan Martianus Capella (5th century CE) expressed th
- `WP:244588-19` (wikipedia) Heliocentrism: Prior to the publication of De Revolutionibus, the most widely accepted system had been proposed by Ptolemy, in which Earth was the center of the universe and a
- `WP:11034-20` (wikipedia) Fluid dynamics: The concept of pressure is central to the study of both fluid statics and fluid dynamics. A pressure can be identified for every point in a body of fluid, regar

**Unsupported citation ids:** none

