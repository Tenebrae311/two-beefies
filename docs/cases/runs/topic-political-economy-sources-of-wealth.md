# topic-political-economy-sources-of-wealth

**Question:** What does the Britannica say about Political Economy: Sources of Wealth, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=13.2, n_calls=7, n_vision_calls=0, n_cited=4, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "Political Economy Sources of Wealth", "k": 8})` -> 8 hits
- `search_wikipedia({"query": "Political Economy sources of wealth", "k": 8})` -> 8 hits
- `read_britannica({"cite_id": "EB:383-0"})` -> 1 hits
- `read_britannica({"cite_id": "EB:383-1"})` -> 1 hits
- `read_britannica({"cite_id": "EB:383-2"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:383-0"})` -> 2 hits
- `read_wikipedia({"cite_id": "WP:46044-0"})` -> 1 hits

## Answer

## Answer

Britannica (5th ed., 1815–1817) treats "Political Economy: Sources of Wealth" as a doctrine of national wealth divided among land, labour, and capital, with commodity prices set by supply and demand rather than labour alone. Modern Wikipedia's "Political economy" describes it instead as an interdisciplinary field studying how political and economic systems shape one another, which only became a distinct field in the mid-18th century before economics split off as a separate, mathematical discipline after Marshall (1890).

## Britannica

5th edition (1815–1817), Vol. 17, p. 383, Chap. II "Of the Sources of Wealth" [EB:383-0][EB:383-1][EB:383-2]. It sorts commodities by how supply tracks demand: (1) those industry can multiply with demand (e.g., corn) — price fairly uniform, pushed up by land scarcity but held down by machinery and improved labour; (2) nature-abundant goods like butcher meat — cheap in "rude" times, dearer in "improved" periods; (3) limited/uncertain supply — appendages (wool, hides), fish, metals/minerals. Its core thesis: "All wealth arises from three sources… land, labour, and capital." It rejects Smith's view of labour as the sole force of wealth, arguing price depends entirely on proportion of demand to supply, so unrewarded labour fetches nothing. Land yields a surplus rent paid to the landlord, who "relinquishes to the farmer the profits of cultivation" [EB:383-2].

## Wikipedia

"Political economy" is an interdisciplinary field in political science and economics studying how political and economic systems influence each other; it arose from 16th-century Western moral philosophy, is credited to Smith, Malthus, and Ricardo (physiocrats preceded them), emerged as a distinct field by the mid-18th century, and lost economics as a separate mathematical discipline in the late 19th century (Marshall's *Principles of Economics*, 1890). Modern political economy analyses labour markets, trade, growth, distribution of wealth, and inequality; "economics" denotes the narrower study of the economy apart from politics and society [WP:46044-0]. The counterpart pipeline maps the Britannica page to Wikipedia's "Political economy" and "Factors of production."

## What changed

- **LANGUAGE**: Archaic OCR spellings (long s read as "f": "ſort," "cafe," "induſtry"); "rude periods"/"improved state of society" vs. modern "developed/developing."
- **KNOWLEDGE**: Britannica offers a substantive theory — three sources of wealth and a supply/demand theory of price explicitly correcting Smith's labour theory of value [EB:383-2]. Wikipedia describes political economy as an academic field/institution, noting the economics–political economy split (post-1890) and listing modern concerns (inequality, trade, growth) absent from Britannica.
- **PERSPECTIVE**: Britannica assumes a stadial "rude → improved" society, class roles (landlord drawing rent "without risk or trouble"), and Eurocentric comparisons (Buenos Ayres, Spain) [EB:383-1]; Wikipedia is neutral, interdisciplinary, and incorporates Marx, class/power relations, and global inequality [WP:46044-0].

## Confidence

High for Britannica (full chapter text read directly). Medium for Wikipedia (introduction read; later sections not verified). No image comparison needed — page not illustrated.

## Citations

- `EB:383-0` (britannica) Political Economy: Sources of Wealth: POLITICAL ECONOMY. Chap. II. The ſecond ſort is of thoſe which human induſtry can multiply in proportion to the demand. Where the commodity, as corn, is ſuch as
- `EB:383-1` (britannica) Political Economy: Sources of Wealth: The third ſort conſiſts of thoſe, in the multiplication of which the power of man is either limited or uncertain. In theſe the rule is various. Some commodities
- `EB:383-2` (britannica) Political Economy: Sources of Wealth: Smith has treated of the revenue derived from theſe three ſources as forming the conſituent parts of the price of commodities; and with regard to labour in part
- `WP:46044-0` (wikipedia) Political economy: Political economy – sometimes referred to as comparative economy – is an interdisciplinary field in political science and economics that studies the relationshi

**Unsupported citation ids:** none

