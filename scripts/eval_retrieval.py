"""Counter-check for the Retrieval/Rerank stages: is the right page found for its topic?

For every indexed Britannica page, query its title and check whether the page is in the
top 5 - with full-text/vector candidates alone and with the Nemotron reranker on top.
Writes docs/ablations/retrieval.md.

Usage: uv run python scripts/eval_retrieval.py
"""

from two_beefies import config, retrieval

OUT = config.ROOT / "docs" / "ablations" / "retrieval.md"


def rank_of(page: int, rerank: bool) -> int | None:
    saved = config.RERANK
    config.RERANK = saved and rerank
    try:
        hits = retrieval.search("britannica", PAGE_TITLES[page], k=20 if not rerank else 5)
    finally:
        config.RERANK = saved
    ranked = list(dict.fromkeys(h["page_index"] for h in hits))
    return ranked.index(page) + 1 if page in ranked else None


def stats(ranks: list[int | None]) -> str:
    hit5 = sum(1 for r in ranks if r and r <= 5)
    mrr = sum(1 / r for r in ranks if r) / len(ranks)
    return f"hit@5 {hit5}/{len(ranks)}, MRR {mrr:.2f}"


PAGE_TITLES: dict[int, str] = {}


def main() -> None:
    pages = [p for p in retrieval.pages() if p["title"]]
    PAGE_TITLES.update({p["page_index"]: p["title"] for p in pages})
    vector = config.RETRIEVAL_BASE_URL and retrieval._has_vectors("britannica")
    mode = "vector (Nemotron Embed)" if vector else "full-text (LanceDB FTS)"
    modes = {"candidates only": False} | ({"+ Nemotron rerank": True} if config.RERANK else {})
    results = {name: [rank_of(p["page_index"], on) for p in pages] for name, on in modes.items()}
    rows = ["| page | title (query) | " + " | ".join(results) + " |",
            "|---|---|" + "---|" * len(results)]
    for i, p in enumerate(pages):
        rows.append(f"| {p['page_index']} | {p['title']} | "
                    + " | ".join(str(results[m][i] or "miss") for m in results) + " |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join([
        "# Ablation: does retrieval find the page for its own topic?", "",
        f"Candidates: {mode}. Query = the page's title (as a user would phrase the topic). "
        "Cell = rank of the page among results (miss = not found).", "",
        *[f"- **{m}**: {stats(r)}" for m, r in results.items()], "",
        *([] if config.RERANK else ["(No model service configured - set RETRIEVAL_BASE_URL "
                                     "to add the rerank column.)", ""]),
        *rows, ""]))
    print("\n".join(f"{m}: {stats(r)}" for m, r in results.items()))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
