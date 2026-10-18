# topic-optical-instruments

**Question:** What does the Britannica say about Optical Instruments, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=21.5, n_calls=7, n_vision_calls=0, n_cited=3, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Optical Instruments", "k": 5})` -> 4 hits
- `search_wikipedia({"query": "Optical Instruments", "k": 5})` -> 5 hits
- `read_britannica({"cite_id": "EB:26-0"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:26-0"})` -> 2 hits
- `search_wikipedia({"k": 5, "query": "Optical instrument"})` -> 5 hits
- `read_wikipedia({"cite_id": "WP:19568-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:603273-0"})` -> 1 hits

## Answer

**1. Answer**

The 5th-edition Britannica (1815–1817) treats "Optical Instruments" as a short practical essay on the magnifying power of simple convex lenses (single microscopes), with a rule and a printed table. Modern Wikipedia has no standalone "Optical Instruments" article; the topic is split across articles such as Microscope and Magnification, which cover many instrument types and optical/digital magnification generally [EB:26-0][WP:19568-0][WP:603273-0].

**2. Britannica**

Britannica, 5th edition (1815–1817), Vol. 15, p. 273: magnifying power of a lens = distance of distinct vision ÷ focal length; an engraving readable at 5 inches is magnified 5×, one readable at 10 inches is magnified 10×; microscopic objects should be judged at about 5 inches' distance; Table I lists diameter/surface/cube magnification for lenses of 1–10 inch focal length (OCR renders the long s as "f", e.g. "lenfes" for lenses) [EB:26-0].

**3. Wikipedia**

Wikipedia: magnification is enlarging the apparent (not physical) size, expressed as a ratio, achieved with optical instruments (magnifying glass, microscope, telescope), printing, or digital processing, without changing perspective [WP:603273-0]. A microscope examines objects too small for the naked eye; types include optical (lenses refracting visible light), fluorescence, electron (TEM/SEM), and scanning-probe microscopes [WP:19568-0].

**4. What changed**

- LANGUAGE: archaic OCR spellings (long s as "f"), inch-based tables, and "diameter/surface/cube" magnification wording vs. modern "magnification ratio" [EB:26-0][WP:603273-0].
- KNOWLEDGE: Britannica covers only single convex lenses with a 5-inch rule-of-thumb table; Wikipedia adds compound instruments, electron/X-ray/scanning-probe microscopes, resolution limits (~0.25 µm, ~1,250×), and angular magnification (tangent formula) — though the core lens formula is shared [EB:26-0][WP:19568-0][WP:603273-0].
- PERSPECTIVE: modest shift from a practical optician's reference (lens-grinding tables, "we maintain") to a neutral, taxonomy-driven encyclopedia spanning instruments beyond visible light [EB:26-0][WP:19568-0].

**5. Confidence**

High for the Britannica reading (full passage retrieved). Medium for the Wikipedia side: no dedicated "Optical Instruments" article exists, so the modern view is assembled via the Microscope and Magnification counterparts; a telescope-oriented treatment may be under-represented.

## Citations

- `EB:26-0` (britannica) Optical Instruments: Part III. O P T I C S. 273 Optical In- struments. Optical In- struments. The one is fo large that it can be cailly read at the distance of ten inches; and the o
- `WP:19568-0` (wikipedia) Microscope: A microscope is a laboratory instrument used to examine objects that are too small to be seen by the naked eye. Microscopy is the science of investigating small
- `WP:603273-0` (wikipedia) Magnification: Magnification is the process of enlarging the apparent size, not physical size, of something. This enlargement is quantified by a size ratio called optical magn

**Unsupported citation ids:** none

