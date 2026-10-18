# plate-giraffe

**Question:** Describe the engraving on the Britannica plate about Giraffe and compare it with how Wikipedia illustrates the subject today.

**Expectation:** vision: should look at the scan (inspect_page_image/compare_images)

**Metrics:** duration_s=32.5, n_calls=8, n_vision_calls=2, n_cited=2, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Giraffe", "k": 5})` -> 1 hits
- `search_wikipedia({"query": "Giraffe", "k": 5})` -> 5 hits
- `read_britannica({"cite_id": "EB:360-0"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:360-0"})` -> 2 hits
- `inspect_page_image({"cite_id": "EB:360-0", "question": "Describe the engraving of the giraffe in detail: the giraffe's pose, coat pattern, neck, head, horns, the human figure for scale, background, and any text labels on the plate."})` -> 1 hits
  - vision answer: The engraving depicts a giraffe standing in profile, facing left, in a landscape setting. The animal has a very long neck, a slender body, and long legs. Its coat is covered in distinct dark spots on a lighter background. A short, erect mane runs along the back of its neck. The head is small with tw
- `read_wikipedia({"cite_id": "WP:12717-0"})` -> 1 hits
- `read_wikipedia({"cite_id": "WP:12717-23"})` -> 1 hits
- `compare_images({"britannica_cite_id": "EB:360-0", "question": "Compare the Britannica 3rd edition engraving of the giraffe (Plate CXXIX, 1788-1797) with the Wikipedia lead image of a giraffe today. How does the depiction differ: pose, setting, realism, presence of human figure, landscape, style?", "wikipedia_cite_id": "WP:12717-0"})` -> 2 hits
  - vision answer: The two images depict the same animal but differ radically in every aspect of presentation, reflecting two centuries of change in illustration technology, purpose, and knowledge.

**Subject and accuracy**
Image 1 (Britannica, Plate CXXIX) is an engraved plate labeled *Cervus Camelopardalis*—a now-ob

## Answer

**Answer** — The Britannica plate is an 18th-century monochrome engraving of a giraffe in profile, labeled "Cervus Camelopardalis" and accompanied by a small human figure with a bow for scale; Wikipedia illustrates the article with a color photograph of a living giraffe in a savanna setting, with no human figure and current taxonomic classification.

**Britannica** — Plate CXXIX, Encyclopaedia Britannica, 3rd edition (1788–1797), Volume 4. The scan shows a full-body engraved giraffe standing in profile facing left: very long neck, slender body, long legs, short erect mane, small horn-like ossicones, large eyes, pointed ears, and a tufted tail; the coat has distinct dark spots on a light ground. To the left stands a small nude human figure, described as a native person holding a bow and arrow, giving scale. Background: cloudy sky, distant hazy hills, sparse vegetation. Labels read "CERVUS. Camelopardalis." at top center, "Plate CXXIX." top right, and "J. B. B. delin. sculp. et publ." (partially legible) bottom right [EB:360-0].

**Wikipedia** — Giraffe article: the lead image is a full-color photograph of a giraffe in profile in tall dry grass with acacia-like trees and a tree-covered hillside behind. The text classifies giraffes as genus *Giraffa*, family Giraffidae, closest extant relative the okapi; traditionally one species (*G. camelopardalis*, nine subspecies), with newer proposals of four species [WP:12717-0].

**What changed**
- KNOWLEDGE: Britannica files the giraffe under "Cervus" (a deer) — a taxonomic error since corrected; modern works place it in *Giraffa*/Giraffidae. The engraving's evenly spaced isolated spots and straight spike-like ossicones are anatomically approximate; the photograph shows real irregular chestnut patches and tufted ossicones.
- PERSPECTIVE: the engraved plate uses an exoticized "native" human with a bow as a scale prop, centering human wonder at the animal's size; the Wikipedia photo presents the giraffe alone in its own habitat, with no human presence.
- LANGUAGE: the Latin plate label "Cervus Camelopardalis" is replaced by "Giraffa" and the technical term "ossicones."

**Confidence** — high. The plate scan, the counterpart match, and the image comparison directly support all claims; the only uncertain detail is the partly legible artist attribution "J. B. B."

## Citations

- `EB:360-0` (britannica) Giraffe: This is Plate CXXIX from the Encyclopaedia Britannica, depicting a giraffe, labeled at the top as "CERVUS. Camelopardalis." The central figure is a full-body en
- `WP:12717-0` (wikipedia) Giraffe: Giraffes (genus Giraffa) are large African hoofed mammals. They are the tallest living terrestrial animals and the largest ruminants on Earth. They are classifi

**Unsupported citation ids:** none

