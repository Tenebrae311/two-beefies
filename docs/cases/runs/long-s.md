# long-s

**Question:** Find Britannica passages that use the word 'such'.

**Expectation:** failure risk (Parse/OCR): long s is transcribed as 'ſ' or 'f' ('ſuch', 'fuch')

**Metrics:** duration_s=11.8, n_calls=5, n_vision_calls=0, n_cited=7, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=None, suggested_stage=None

## Tool calls

- `search_britannica({"query": "such", "k": 10})` -> 0 hits
- `search_britannica({"query": "fuch", "k": 10})` -> 7 hits
- `read_britannica({"cite_id": "EB:1126-3"})` -> 1 hits
- `read_britannica({"cite_id": "EB:356-2"})` -> 1 hits
- `read_britannica({"cite_id": "EB:2069-1"})` -> 1 hits

## Answer

**Finding:** A search for the literal string **"such"** in Britannica returns **no results**. This is because the OCR renders the 18th/19th-century long s as "f", so the word appears as **"fuch"**.

Searching for **"fuch"** returns 7 passages across 5 articles:

| Citation | Article | Edition | Example |
|----------|---------|---------|---------|
| EB:1126-3 | Miniature-Painting: Flowers | 3rd (1788-1797) | "without repeating **fuch** as have been mentioned already" |
| EB:356-2 | Catechism and Catechumens | 3rd (1788-1797) | "or **fuch** as were appointed to be baptized" |
| EB:2069-1 | Britain 1795 War and Politics | 4th (1801-1810) | "put to death **fuch** of their countrymen" |
| EB:356-0 | Catechism and Catechumens | 3rd (1788-1797) | "Thofe who give **fuch** inftructions" |
| EB:1718-2 | Ardebil, Arden | 3rd (1788-1797) | "applicable to **fuch** very different fites" |
| EB:895-1 | Lizards and Crocodiles | 5th (1815-1817) | (long s OCR throughout page) |
| EB:895-3 | Lizards and Crocodiles | 5th (1815-1817) | (long s OCR throughout page) |

**Bottom line:** The word "such" does occur in these Britannica passages, but you must search for the OCR variant **"fuch"** (the long s rendered as "f") to find it. A literal "such" search will miss every instance. If you want, I can read the full text of any of these passages, or search additional OCR variants.

## Citations

- `EB:1126-3` (britannica) Miniature-Painting: Flowers: tures, and every thing elfe in miniature, touched in as grand, as true, and as noble a manner (though more tender and delicate), as they are in oil. However, pa
- `EB:356-2` (britannica) Catechism and Catechumens: There were four orders or degrees of catechumens; the firſt were thoſe inftructed privately without the church, and kept at a diſtance for fome time from the pr
- `EB:2069-1` (britannica) Britain 1795 War and Politics: overpowered by the republicans, who, according to their cuftom, put to death fuch of their countrymen as they found in arms fighting againft them. By this feebl
- `EB:356-0` (britannica) Catechism and Catechumens: C A T. [ 250 ] C A T Catechetic Catechu- men. frution given any perfom in the first rudiments of an art or science; but more particularly of the Chriſtian relig
- `EB:1718-2` (britannica) Ardebil, Arden: by Olfian in mentioning the woods of Caledonia, it cannot (fays Mr Whitaker) be compounded of ar the prepotitive article in Celtic, and the fubftantive den, as 
- `EB:895-1` (britannica) Lizards and Crocodiles: " Mr Smith of Bedford obferves to me on the word dragon, as follows: Mr Jacob Bobart, botany profeffor (or rather fuperintendent of the garden) of Oxford, did a
- `EB:895-3` (britannica) Lizards and Crocodiles: The crocodile fometimes arrives at a very great fize. Individuals of 20 feet long have frequently been feen, and infances are mentioned of fome which have excee

**Unsupported citation ids:** none

