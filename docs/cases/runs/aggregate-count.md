# aggregate-count

**Question:** How many of the indexed Britannica pages are about medicine?

**Expectation:** failure risk (Retrieval): aggregate question that top-k retrieval cannot answer

**Metrics:** duration_s=16.5, n_calls=5, n_vision_calls=0, n_cited=8, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "medicine", "k": 10})` -> 3 hits
- `search_britannica({"query": "physician", "k": 10})` -> 0 hits
- `search_britannica({"k": 10, "query": "surgery surgeon"})` -> 0 hits
- `search_britannica({"k": 10, "query": "hospital disease plague"})` -> 5 hits
- `search_britannica({"k": 10, "query": "anatomy physician doctor apothecary pharmacy"})` -> 1 hits

## Answer

I can't give you an exact count. The Britannica search tool returns only the top‑k relevance‑ranked passages per query (capped at 10), and it has no category filter, no "list all indexed pages," and no total‑count endpoint. So "how many indexed pages are about medicine" isn't something I can compute exhaustively from these tools.

What my searches did surface (a relevance sample, not a count) that is clearly or partly medical:

- **EB:571-0** and **EB:571-1** — "Surgery: Inflammation Treatment," 2nd edition (1778–1783), Volume 10 — directly medical/surgical.
- **EB:1139-2** and **EB:1139-3** — "Bills of Mortality," 4th–6th supplement (1815–1824) — mortality/disease statistics, adjacent to medicine.
- Tangential mentions only (not really "about medicine"): EB:108-3 Rock Crystal ("medicinal uses"), EB:952-3 London Wards and Buildings (leper hospital), EB:895-1 Lizards and Crocodiles ("physic garden"), EB:1728-1 Baghdad.

Searches for "physician" and "surgery surgeon" returned no matches, likely due to OCR/long‑s spelling issues in the 18th/19th‑century text.

**Bottom line:** I found a handful of medicine‑related pages, but the indexed corpus (editions 1–8, 1768–1860) is far larger than these samples, and the tool doesn't support counting by topic. If you need a real number, you'd need access to the full index metadata or a way to enumerate all pages and classify them — which this search interface doesn't provide.

## Citations

- `EB:571-0` (britannica) Surgery: Inflammation Treatment: Part II. S U R G E R Y. 8379 Theory. Theory. either with a view to reſolve or ſuppurate. Thus it might be dangerous to make uſe of repellent applica- tions, at 
- `EB:571-1` (britannica) Surgery: Inflammation Treatment: itſelf, which generally acts alſo as a ſedative. A- mong the latter we may place, in the firſt place, the mild expreſſed oils, as alſo the ſoft ointments made w
- `EB:1139-2` (britannica) Bills of Mortality: Some parish registers in Germany appear to have commenced with the sixteenth century: and in the Göttliche Ordnung of Suissmilch (T. 3. S. 23.), we are informed
- `EB:1139-3` (britannica) Bills of Mortality: This book of Graunt's, although the first, is also one of the best that have been published on the sub- ject. It contains many judicious observations on the imp
- `EB:108-3` (britannica) Rock Crystal Properties and Classification: the world; but that which is formed of hexagonal columns, affixed to a ſolid baſe at one end, and ter- minated by a hexagonal column at the other, is in- finite
- `EB:952-3` (britannica) London Wards and Buildings: 1600, was barely ſeparated from Broad-ſtreet. The church was peopled to have belonged to an hoſpital for lepers, founded about the year 1117, by Matilda queen t
- `EB:895-1` (britannica) Lizards and Crocodiles: " Mr Smith of Bedford obferves to me on the word dragon, as follows: Mr Jacob Bobart, botany profeffor (or rather fuperintendent of the garden) of Oxford, did a
- `EB:1728-1` (britannica) Baghdad: banks of the Tigris received the name of the Camp, or Fortreſs, of Al Mohdi. The khalif had a fu- perb and magnificent palace both in the caſtern and weſtern pa

**Unsupported citation ids:** none

