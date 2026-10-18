# topic-economists-on-majority-rule

**Question:** What does the Britannica say about Economists on Majority Rule, and how does modern Wikipedia describe it? What changed: language, knowledge or perspective?

**Expectation:** success candidate: indexed page with a Wikipedia counterpart

**Metrics:** duration_s=16.2, n_calls=8, n_vision_calls=0, n_cited=8, n_unsupported=0, support=None, n_weak_claims=0, gold_page_found=True, suggested_stage=None

## Tool calls

- `search_britannica({"query": "economists majority rule", "k": 10})` -> 10 hits
- `search_wikipedia({"query": "economists majority rule", "k": 10})` -> 10 hits
- `read_britannica({"cite_id": "EB:122-0"})` -> 1 hits
- `read_britannica({"cite_id": "EB:122-1"})` -> 1 hits
- `read_britannica({"cite_id": "EB:122-2"})` -> 1 hits
- `read_britannica({"cite_id": "EB:122-3"})` -> 1 hits
- `find_counterparts({"britannica_cite_id": "EB:122-0"})` -> 2 hits
- `read_wikipedia({"cite_id": "WP:658906-0"})` -> 1 hits

## Answer

**Answer** — Britannica's "Economists on Majority Rule" (4th–6th supplement, 1815–1824) records the Physiocrats' rejection of majority rule: government must rest on evidence, not vote-counting, because majorities can be moved by private interest and ignorance [EB:122-0][EB:122-1]. Modern Wikipedia describes majority rule as a formal social-choice rule — the option preferred by more than half the voters wins — with criteria such as May's theorem and discussion of minority rights [WP:658906-0][WP:658906-4].

**Britannica** — The "Economists" (Physiocrats) argue plurality of suffrage is no security: divisions of opinion come only from ignorance or bad design, and numbers cannot make the non-evident evident [EB:122-0]. The greatest evil is that majority rule sets private interest against the public interest, "which is sure to be sacrificed" [EB:122-1]. Rule by votes gives "despotical authority" to numbers where only evidence should govern, leaving the nation unprotected, and an uninstructed nation is split between rich and poor, each regarding the other as prey [EB:122-2][EB:122-3].

**Wikipedia** — Majority rule is a social-choice rule in which the option preferred by over half the voters wins; it is one of two major notions of democracy (alongside the utilitarian rule), used in parliamentary procedure, generalized by Condorcet's principle, and axiomatized by May's theorem (anonymity, neutrality, decisiveness, positive response); the article also covers supermajority rules and minority-rights protections [WP:658906-0][WP:658906-4][WP:658906-3][WP:658906-7].

**What changed**
- LANGUAGE: archaic idiom ("plurality of suffrage," "deliberants," "prepossession") versus modern social-choice vocabulary.
- KNOWLEDGE: Britannica gives philosophical objections only; Wikipedia adds vote thresholds, May's theorem, the Condorcet principle, supermajority rules, and voting paradoxes.
- PERSPECTIVE: Britannica is elitist and technocratic — rule by evidence and enlightened experts, distrust of the masses "sunk in ignorance and prejudices" and of the poor envying the rich; Wikipedia is neutral and institutional, including how majority rule can protect minority rights [EB:122-3][WP:658906-7].

**Confidence**: high — based on the full Britannica passage and Wikipedia's lead section; the counterpart pipeline links the Britannica page to both "Physiocracy" and "Majority rule."

## Citations

- `EB:122-0` (britannica) Economists on Majority Rule: 720 Economists. To this the Economists made answer, that, if the opposition of one will can suspend the effect of all the others, it reduces authority to inacti
- `EB:122-1` (britannica) Economists on Majority Rule: But the greatest evil, they said, of the mode of determining, by majority of votes, the question respecting the social order, was, that it set individual intere
- `WP:658906-0` (wikipedia) Majority rule: In social choice theory, the majority rule (MR) is a social choice rule which says that, when comparing two options (such as bills or candidates), the option pr
- `WP:658906-4` (wikipedia) Majority rule: Kenneth May proved that the simple majority rule is the only "fair" ordinal decision rule, in that majority rule does not let some votes count more than others 
- `EB:122-2` (britannica) Economists on Majority Rule: der this system, it is not evidence,” they said, Economists, “ which governs; it is opinion, or the will of a certain number of men actuated by the same opinion
- `EB:122-3` (britannica) Economists on Majority Rule: “ So long, on the other hand, as a nation is not thus instructed, the people, properly so called, sunk in ignorance and prejudices, see no farther than the near
- `WP:658906-3` (wikipedia) Majority rule: Parliamentary rules may prescribe the use of a supermajoritarian rule under certain circumstances, such as the 60% filibuster rule to close debate in the US Sen
- `WP:658906-7` (wikipedia) Majority rule: A super-majority rule actually empowers the minority, making it stronger (at least through its veto) than the majority. McGann argued that when only one of mult

**Unsupported citation ids:** none

