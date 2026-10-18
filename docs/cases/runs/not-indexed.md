# not-indexed

**Question:** What did the Britannica say about the steam locomotive?

**Expectation:** should admit that no indexed page covers it

**Metrics:** duration_s=23.7, n_calls=16, n_vision_calls=0, n_cited=4, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "steam locomotive", "k": 5})` -> 1 hits
- `search_wikipedia({"query": "steam locomotive", "k": 5})` -> 5 hits
- `search_britannica({"k": 5, "query": "locomotive"})` -> 0 hits
- `search_britannica({"k": 5, "query": "railway engine"})` -> 5 hits
- `search_britannica({"k": 5, "query": "steam engine"})` -> 4 hits
- `search_britannica({"k": 5, "query": "rail road"})` -> 4 hits
- `search_britannica({"k": 5, "query": "railway"})` -> 1 hits
- `search_britannica({"k": 5, "query": "Stephenson"})` -> 0 hits
- `search_britannica({"k": 5, "query": "locomotive engine"})` -> 4 hits
- `search_britannica({"k": 5, "query": "Trevithick"})` -> 0 hits
- `search_britannica({"k": 5, "query": "steam"})` -> 1 hits
- `search_britannica({"k": 5, "query": "engine"})` -> 4 hits
- `search_britannica({"k": 5, "query": "Watt"})` -> 0 hits
- `search_britannica({"k": 5, "query": "rail-road"})` -> 4 hits
- `search_britannica({"k": 5, "query": "locomotives"})` -> 0 hits
- `search_britannica({"k": 5, "query": "steam-engine"})` -> 4 hits

## Answer

I was unable to find a dedicated article on the steam locomotive in the Encyclopaedia Britannica (editions 1–8, 1768–1860). I ran multiple searches — "steam locomotive", "locomotive", "locomotives", "railway engine", "rail road", "rail-road", "steam engine", "steam-engine", "engine", "steam", "Trevithick", "Stephenson", and "Watt" — and none returned a standalone locomotive entry.

The closest related material in the corpus:

- **EB:641-0 / EB:641-1**, "Bridges and Viaducts", 8th edition (1853–1860), Volume 12 — an illustrated plate of railway bridges (Britannia Tubular Bridge, Royal Border Bridge, Crumlin Viaduct, etc.), including a "Christiania Railway Bridge" caption. This concerns bridge engineering, not the locomotive itself.
- **EB:653-2 / EB:653-3**, "Coak and Coalery", 4th–6th supplement (1815–1824), Volume 3 — a coal-mining passage mentioning an "engine-level drift," but nothing about locomotives.

**Bottom line:** The Britannica corpus available here appears to contain no dedicated steam locomotive article, so I cannot report what it said on the subject. The steam locomotive (Trevithick 1804, Stephenson's *Rocket* 1829) falls squarely within the 1768–1860 window, so its absence may reflect a gap in this particular OCR'd corpus rather than the original editions. If you have a specific edition or page in mind, I can look it up directly.

## Citations

- `EB:641-0` (britannica) Bridges and Viaducts: BRITANNIA TUBULAR BRIDGE ROYAL CRESSENT BRIDGE, BATH ROYAL VIADUCT BRIDGE OVER THE RHINE AT COBLENZ CHRISTIANIA RAILWAY BRIDGE VIADUCT, SUSPENSION BRIDGE SUSPEN
- `EB:641-1` (britannica) Bridges and Viaducts: This plate from the Encyclopaedia Britannica depicts various types of bridges, illustrating civil engineering designs. From left to right, the figures show: the
- `EB:653-2` (britannica) Coak and Coalery: surface to the seam C, with great facility. In prosecuting the working of the coal from the pit f, towards the bore-hole C, a down-throw slip- dike gg, is met w
- `EB:653-3` (britannica) Coak and Coalery: carried forward towards the rise of the seam to L, where it will cut the bore-hole b, f, and allow the coal-pit to be sunk from f to L, and the dike gg having b

**Unsupported citation ids:** none

