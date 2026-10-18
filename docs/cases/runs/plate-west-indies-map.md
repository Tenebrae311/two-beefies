# plate-west-indies-map

**Question:** Describe the engraving on the Britannica plate about West Indies Map and compare it with how Wikipedia illustrates the subject today.

**Expectation:** vision: should look at the scan (inspect_page_image/compare_images)

**Metrics:** duration_s=28.5, n_calls=4, n_vision_calls=2, n_cited=2, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "West Indies Map plate engraving", "k": 10})` -> 10 hits
- `search_wikipedia({"query": "West Indies map", "k": 10})` -> 10 hits
- `inspect_page_image({"cite_id": "EB:289-0", "question": "Describe the engraving in detail: the title cartouche, the scale bar, the labeled islands and coasts (Florida, Bahamas, Cuba, Hispaniola, Jamaica, Puerto Rico, Leeward/Windward Islands, Mexico, New Granada, Guiana), the oceans, the lettering style, and any decorative elements or engraver attribution."})` -> 1 hits
  - vision answer: The page displays an engraved map titled "WEST INDIES" within an oval cartouche in the upper right corner. The map covers the Caribbean region, including Florida, the Bahamas, Cuba, Hispaniola, Jamaica, Puerto Rico, the Leeward and Windward Islands, Mexico, New Granada, and Guiana. It shows the Gulf
- `compare_images({"britannica_cite_id": "EB:289-0", "wikipedia_cite_id": "WP:5574915-1", "question": "How did the depiction of the West Indies change from this 1780s Britannica engraving (Plate CCLV) to the modern Wikipedia illustration? Cover projection/accuracy, what is shown (islands, coasts), labeling and place names, political boundaries, color, and purpose."})` -> 2 hits
  - vision answer: The 1780s Britannica engraving and the modern Wikipedia illustration depict the West Indies in fundamentally different ways, reflecting changes in cartographic science, purpose, and visual conventions.

**Projection and accuracy**
The Britannica plate is a flat, rectangular map with a graticule of l

## Answer

**Answer** — The Britannica plate is Plate CCLV, an engraved West Indies map from the 3rd edition (1788–1797) attributed to "H. Moll geogr. London" [EB:289-0]. Wikipedia illustrates the same subject today with a modern digital locator globe that highlights the island chain in green and carries no text labels [WP:5574915-1]. The old plate names islands, mainland coasts, and oceans in dense capitalized lettering; the modern image uses color only, showing where the West Indies lie relative to the Americas [EB:289-0][WP:5574915-1].

**Britannica** — Plate CCLV, "West Indies Map," Encyclopaedia Britannica, 3rd edition (1788–1797), Volume 9. The monochrome engraving (black ink on aged paper) has an oval cartouche titled "WEST INDIES" (upper right), a scale bar reading "Miles to a Degree," a latitude/longitude graticule, and labels for Florida, the Bahamas, Cuba, Hispaniola, Jamaica, Puerto Rico, the Leeward and Windward Islands, Mexico, New Granada, Guiana, the Gulf of Mexico, Caribbean Sea, Atlantic Ocean, and South Sea; the bottom reads "H. Moll geogr. London" and the plate is marked "Plate CCLV" [EB:289-0].

**Wikipedia** — The "West Indies" article's lead image is a digital globe on an orthographic-style projection centered on the Atlantic, showing Earth's curvature with a great-circle grid [WP:5574915-1]. All land outside the West Indies is gray, oceans are white, and the island chain is highlighted in green; modern national boundaries appear as thin white lines, but the highlighted region has no internal borders and no labels for islands, countries, or bodies of water [WP:5574915-1].

**What changed**
- LANGUAGE: archaic, fully capitalized engraving lettering ("HISPANIOLA," "PORTO RICO," "CARIBBEAN SEA," "TERRA FIRMA") versus no text at all; historical names such as "New Granada" and "Terra Firma" have disappeared [EB:289-0][WP:5574915-1].
- KNOWLEDGE: generalized, hand-engraved 18th-century coastlines versus satellite-derived modern boundaries and an accurate projection; colonial place names replaced by present-day geography [EB:289-0][WP:5574915-1].
- PERSPECTIVE: Britannica frames the region through European colonial spheres and mainland approaches; Wikipedia frames the West Indies as a single geographic archipelago [EB:289-0][WP:5574915-1].

**Confidence** — high. Both the plate description and the cross-source image comparison come directly from tool output on the original scan and the Wikipedia image; I did not verify the Wikipedia image's file metadata independently.

## Citations

- `EB:289-0` (britannica) West Indies Map: Plate CCLV. WEST INDIES ATLANTIC OCEAN CARIBBEAN SEA GULF of MEXICO FLORIDA BAHAMA ISLANDS CUBA HISPANIOLA JAMAICA PORTO RICO LEEWARD ISLANDS WINDWARD ISLANDS L
- `WP:5574915-1` (wikipedia) West Indies: The English term Indie is derived from the Classical Latin India, a reference to the territories in South Asia adjacent and east to the Indus River. India is bo

**Unsupported citation ids:** none

