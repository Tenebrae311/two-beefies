# topic-rock-crystal-properties-and-classification

**Question:** What does the Britannica say about Rock Crystal Properties and Classification, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=22.8, n_calls=10, n_vision_calls=0, n_cited=8, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "rock crystal properties classification", "k": 10})` -> 10 hits
- `search_wikipedia({"query": "rock crystal properties classification quartz", "k": 10})` -> 10 hits
- `read_britannica({"cite_id": "EB:108-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:25233-3"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:25233-5"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:25233-1"})` -> 1 hits
- `read_britannica({"cite_id": "EB:108-1"})` -> 1 hits
- `read_britannica({"cite_id": "EB:108-2"})` -> 1 hits
- `read_britannica({"cite_id": "EB:108-3"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:25233-4"})` -> 1 hits

## Answer

**Answer**
The Britannica's 4th edition (1801–1810) article "Rock Crystal Properties and Classification" describes rock crystal by its form, colour, and accidents, coloured by metallic oxides and classed among "false gems." Modern Wikipedia's Quartz article describes rock crystal as pure, colorless quartz, classified by crystal structure, polymorphism, and impurity-driven colour, with piezoelectric applications — a shift from gemology to mineral science.

**Britannica** — 4th ed. (1801–1810), Vol. 6 Part 2, Conchology–Crystallization [EB:108-0–3]. Coloured crystals owe their tinge to "an exceedingly small portion of metallic oxide," lost when strongly heated; sold as "false gems": false rubies, topazes, emeralds, amethysts, sapphires [EB:108-0]. Fourcroy classifies them by form, colour (diaphanous, reddish, smoky, blackish), and accidents (hollow, water-bearing, pebble-form) [EB:108-0,1]. Three geometric orders of pure crystal (18-plane columnar; 12/16-plane double pyramids; imperfect single pyramids) plus a fourth "metallic crystals" order; aqua fortis distinguishes crystal from spars [EB:108-2]. Crystals were once fluid; Bergman grew crystals from quartz powder and "suor" (sulfuric) acid [EB:108-3].

**Wikipedia** — Quartz article. Rock crystal = pure, colorless, transparent/translucent quartz; coloured varieties (amethyst, citrine, rose, smoky, milky) get colour from impurities altering molecular orbitals/electronic transitions [WP:25233-5]. Quartz occurs as α-quartz (trigonal) and β-quartz (hexagonal), switching at 573 °C, in chiral space groups; ideal habit is a six-sided prism with pyramidal ends, often twinned [WP:25233-3,4]. "Rock crystal" is the traditional name for transparent coarsely crystalline quartz; Greeks called it supercooled ice [WP:25233-1]. Piezoelectricity (Curie, 1880) enables oscillators and clocks [WP:25233-6,14].

**What changed**
- LANGUAGE: archaic OCR spellings ("cryſtal," "falſe," "aqua fortis," "suor acid") vs modern mineral terminology [EB:108-0–3 vs WP:25233-1,5].
- KNOWLEDGE: colour from metallic oxides and fire resistance vs impurity-driven electronic transitions and α/β polymorphs at 573 °C; piezoelectricity, space groups, chirality, chalcedony/moganite are new [EB:108-0,2,3 vs WP:25233-3,5,6].
- PERSPECTIVE: gems/jewels and medicinal uses vs rock-forming mineral (~12% of lithosphere) and electronics/industrial uses [EB:108-0,3 vs WP:25233-7,12,14].

**Confidence**: high. Both sources directly cover rock crystal properties/classification. Only the 4th Britannica edition was located; later editions and the rest of the Wikipedia article were not checked.

## Citations

- `EB:108-0` (britannica) Rock Crystal Properties and Classification: C R Y [ 782 ] C R Y pyramid, and are of various colours; or they lie in clayey earths, and have both pyramids, but no prim. They are found at Blackenburg upon t
- `EB:108-2` (britannica) Rock Crystal Properties and Classification: many it is found ſtained with the colours of the ruby, ſapphire, emerald, and topaz; in which cafe jewellers take great advantage of it, feeling it under the na
- `EB:108-3` (britannica) Rock Crystal Properties and Classification: the world; but that which is formed of hexagonal columns, affixed to a ſolid baſe at one end, and ter- minated by a hexagonal column at the other, is in- finite
- `WP:25233-5` (wikipedia) Quartz: Pure quartz, traditionally called rock crystal or clear quartz, is colorless and transparent or translucent. Colored varieties of quartz are common and include 
- `WP:25233-3` (wikipedia) Quartz: Quartz can form as two distinct polymorphs depending on the temperature and pressure: α-quartz (also called low quartz or normal quartz) and β-quartz (also call
- `WP:25233-1` (wikipedia) Quartz: The word quartz is derived from the German word Quarz, which had the same form in the first half of the 14th century in Middle High German and in East Central G
- `WP:25233-6` (wikipedia) Quartz: Quartz crystals have piezoelectric properties; they develop an electric potential upon the application of mechanical stress. Quartz's piezoelectric properties w
- `WP:25233-7` (wikipedia) Quartz: Quartz is the second most abundant mineral or mineral group in the Earth's lithosphere; by mass, the feldspar group comprises 41% of the lithosphere, followed b

**Unsupported citation ids:** none

