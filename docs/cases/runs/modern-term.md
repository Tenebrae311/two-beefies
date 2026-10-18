# modern-term

**Question:** What does the Britannica say about sundials?

**Expectation:** failure risk (Retrieval): the 1771 page says 'dial', not 'sundial'

**Metrics:** duration_s=17.4, n_calls=11, n_vision_calls=0, n_cited=3, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "sundials", "k": 10})` -> 0 hits
- `search_wikipedia({"query": "sundial", "k": 5})` -> 5 hits
- `search_britannica({"k": 10, "query": "fundials"})` -> 0 hits
- `search_britannica({"k": 10, "query": "sun-dials"})` -> 5 hits
- `search_britannica({"k": 10, "query": "gnomon"})` -> 1 hits
- `read_britannica({"cite_id": "EB:2465-0"})` -> 1 hits
- `read_britannica({"cite_id": "EB:2465-1"})` -> 1 hits
- `read_britannica({"cite_id": "EB:2465-2"})` -> 1 hits
- `read_britannica({"cite_id": "EB:2465-3"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:2465-0"})` -> 2 hits
- `read_wikipedia({"cite_id": "WP:72907-0"})` -> 1 hits

## Answer

## Answer

The 1st edition Encyclopaedia Britannica (1768–1771) treats sundials as a practical, geometric craft: how to draw hour-lines on a wall or plane, how to set a dial true using a watch, quadrant, or solar altitudes, and how foreign (Babylonian/Italian) dials count hours from sunrise and sunset. Modern Wikipedia defines a sundial as a horological device telling civil time via the Sun's position, with a gnomon whose style is parallel to Earth's axis at an angle equal to latitude, valued now as decoration and mathematical study.

## Britannica

1st edition (1768–1771), Volume 2 (C–L), p. 429, "Sundial Construction and Types" [EB:2465-0 to EB:2465-3]. It describes a dial read by stereographic projection whose moon markings let you read the sun's declination and day length by inspection; Babylonian and Italian dials reckon hours from sunrise/sunset rather than noon, so they perpetually differ from clocks (in Italy the day begins at mid-twilight, the Ave Maria). It notes better timekeeping instruments have made such dials of little account, though their theory is ingenious and they remain handy for "vulgar use." It gives construction rules (tangents of hour-distances, co-tangents of solar altitudes) and methods to set a dial true: an equinoctial ring-dial, solar altitude with a (Hadley's) quadrant, equal morning/afternoon altitudes to correct a watch, and a meridian line made with a pinhole plate inclined at the co-latitude.

## Wikipedia

"A sundial is a horological device that tells the time of day (civil time) … by the apparent position of the Sun" — a dial plate plus gnomon casting a shadow on hour-lines; the style (time-telling edge) must be parallel to Earth's rotational axis, its angle above horizontal equal to latitude; sundials are now decorative objects, metaphors, and objects of mathematical study, and cheap mass-produced ones are often misaligned [WP:72907-0].

## What changed

- **LANGUAGE**: OCR long-s renders "sun" as "fun," "instrument" as "inftrument"; archaic terms ("vulgar use," "stile," Babylonian/Italian dials).
- **KNOWLEDGE**: Britannica gives pre-industrial practical methods for regulating clocks and laying out dials by geometry; Wikipedia states the axial/latitude alignment rule and frames time as civil time.
- **PERSPECTIVE**: Britannica is instructional and practical for the builder, with religious framing (Ave Maria); Wikipedia is encyclopedic, emphasizing decoration and intrigue.
- **NO_COUNTERPART**: Wikipedia's digital sundials, national sundial societies, and equation-of-time discussion have no Britannica equivalent; Britannica's pinhole meridian line and Italian twilight reckoning have no Wikipedia counterpart here.

## Confidence

High on the Britannica content (full passage read). Medium on the comparison, since I read only Wikipedia's introduction, not the full article, and only the 1st Britannica edition surfaced — later editions (2nd–8th, through 1860) may cover sundials differently.

## Citations

- `EB:2465-0` (britannica) Sundial Construction and Types: D I A ( 429 ) D I A fladow of that perpendicular edge is a vertical circle paffing through the fun, in the ftereographic projection. The moon being duly marked 
- `EB:2465-3` (britannica) Sundial Construction and Types: Or, in ſummer, take two equal altitudes of the fun in the ſame day ; one any time between 7 and 10 in the morning, the other between 2 and 5 in the afternoon ; 
- `WP:72907-0` (wikipedia) Sundial: A sundial is a horological device that tells the time of day (referred to as civil time in modern usage) when direct sunlight shines by the apparent position of

**Unsupported citation ids:** none

