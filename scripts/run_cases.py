"""Run candidate questions through the QA agent, measure them, and save traces.

For every candidate: docs/cases/runs/<slug>.json (full trace) and <slug>.md (readable),
then docs/cases/summary.md with metrics over ALL saved runs. Pick 3 successes + 3
failures and annotate them in docs/cases/annotations.json:
  {"<slug>": {"verdict": "success"|"failure", "stage": "<pipeline stage>",
              "why": "...", "reveals": "..."}}
Pipeline stages used for the failure typology: Parse/OCR, Retrieval, Rerank,
Agent reasoning, Grounding.

Usage: uv run python scripts/run_cases.py [--topics 8] [--only slug1,slug2] [--summary-only]
"""

import json
import re
import sys
import time
from datetime import datetime, timezone

from two_beefies import config, retrieval
from two_beefies.qa import ask

CASES = config.ROOT / "docs" / "cases"
OUT = CASES / "runs"
VISION_TOOLS = {"inspect_page_image", "compare_images"}

# Fixed probes for known weak spots: (slug, question, expectation)
PROBES = [
    ("ambiguity-mercury", "What does each source say about Mercury?",
     "failure risk (Retrieval): ambiguous term - planet, god or metal"),
    ("aggregate-count", "How many of the indexed Britannica pages are about medicine?",
     "failure risk (Retrieval): aggregate question that top-k retrieval cannot answer"),
    ("not-indexed", "What did the Britannica say about the steam locomotive?",
     "should admit that no indexed page covers it"),
    ("long-s", "Find Britannica passages that use the word 'such'.",
     "failure risk (Parse/OCR): long s is transcribed as 'ſ' or 'f' ('ſuch', 'fuch')"),
    ("modern-term", "What does the Britannica say about sundials?",
     "failure risk (Retrieval): the 1771 page says 'dial', not 'sundial'"),
    ("time-travel", "What did the Britannica of the 1790s say about the history of Baghdad "
     "after 1800?", "should refuse: the source cannot know events after its publication"),
]
TOPIC_TEMPLATE = ("What does the Britannica say about {t}, and how does modern Wikipedia "
                  "describe it? What changed: language, knowledge or perspective?")
PLATE_TEMPLATE = ("Describe the engraving on the Britannica plate about {t} and compare it "
                  "with how Wikipedia illustrates the subject today.")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def candidates(n_topics: int) -> list[dict]:
    """Comparison questions about pages that are actually indexed (with their gold page),
    one question per illustrated plate (vision tools), plus the fixed probes."""
    pages = [p for p in retrieval.pages() if p["title"]]
    text_pages = [p for p in pages if not p["illustrated"]][:n_topics]
    plates = [p for p in pages if p["illustrated"]][:2]
    out = [{"slug": "topic-" + _slug(p["title"]), "question": TOPIC_TEMPLATE.format(t=p["title"]),
            "expectation": "success candidate: indexed page with a Wikipedia counterpart",
            "gold_page": p["page_index"]} for p in text_pages]
    out += [{"slug": "plate-" + _slug(p["title"]), "question": PLATE_TEMPLATE.format(t=p["title"]),
             "expectation": "vision: should look at the scan (inspect_page_image/compare_images)",
             "gold_page": p["page_index"]} for p in plates]
    out += [{"slug": s, "question": q, "expectation": e, "gold_page": None} for s, q, e in PROBES]
    return out


def metrics(out: dict, duration: float, gold_page: int | None) -> dict:
    retrieved_pages = {int(cid.split(":")[1].split("-")[0]) for c in out["trace"]
                       for cid in c.get("cite_ids", []) if cid.startswith("EB:")}
    ev = out.get("evidence") or {}
    claims = ev.get("claims") or []
    m = {
        "duration_s": round(duration, 1),
        "n_calls": len(out["trace"]),
        "n_vision_calls": sum(c["name"] in VISION_TOOLS for c in out["trace"]),
        "n_cited": len(out["citations"]) + len(out["unsupported"]),
        "n_unsupported": len(out["unsupported"]),
        "support": ev.get("support"),
        "n_weak_claims": sum(c["flag"] in ("weak", "unsupported") for c in claims),
        "gold_page_found": (gold_page in retrieved_pages) if gold_page is not None else None,
    }
    # First guess at the failing pipeline stage; the human annotation has the final word.
    if m["gold_page_found"] is False:
        m["suggested_stage"] = "Retrieval"
    elif m["n_unsupported"]:
        m["suggested_stage"] = "Grounding"
    elif claims and m["n_weak_claims"] / len(claims) > 0.3:
        m["suggested_stage"] = "Agent reasoning"
    else:
        m["suggested_stage"] = None
    return m


def to_markdown(run: dict) -> str:
    m = run["metrics"]
    lines = [f"# {run['slug']}", "", f"**Question:** {run['question']}", "",
             f"**Expectation:** {run['expectation']}", "",
             "**Metrics:** " + ", ".join(f"{k}={v}" for k, v in m.items()), "",
             "## Tool calls", ""]
    for c in run["trace"]:
        lines.append(f"- `{c['name']}({json.dumps(c['args'], ensure_ascii=False)})` -> "
                     f"{c.get('n_hits', 0)} hits")
        if c.get("vision"):
            lines.append(f"  - vision answer: {c['vision']['answer'][:300]}")
    lines += ["", "## Answer", "", run["answer"], "", "## Citations", ""]
    for c in run["citations"]:
        lines.append(f"- `{c['cite_id']}` ({c['source']}) {c['title']}: {c['snippet'][:160]}")
    lines += ["", f"**Unsupported citation ids:** {run['unsupported'] or 'none'}", ""]
    if run.get("evidence"):
        lines += ["## Evidence (Nemotron reranker)", ""]
        lines += [f"- {c['flag']} (support {c['support']}): {c['text']}"
                  for c in run["evidence"]["claims"]]
    return "\n".join(lines) + "\n"


def write_summary() -> None:
    runs = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    notes_path = CASES / "annotations.json"
    notes = json.loads(notes_path.read_text()) if notes_path.is_file() else {}
    rows = ["| case | verdict | stage | s | calls | vision | cited | unsupported | support | gold page |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        m, a = r["metrics"], notes.get(r["slug"]) or {}
        rows.append(f"| [{r['slug']}](runs/{r['slug']}.md) | {a.get('verdict') or '-'} | "
                    f"{a.get('stage') or m.get('suggested_stage') or '-'} | {m['duration_s']} | "
                    f"{m['n_calls']} | {m['n_vision_calls']} | {m['n_cited']} | "
                    f"{m['n_unsupported']} | {m['support'] if m['support'] is not None else '-'} | "
                    f"{'-' if m['gold_page_found'] is None else ('yes' if m['gold_page_found'] else 'NO')} |")
    cited = sum(r["metrics"]["n_cited"] for r in runs)
    unsup = sum(r["metrics"]["n_unsupported"] for r in runs)
    gold = [r["metrics"]["gold_page_found"] for r in runs if r["metrics"]["gold_page_found"] is not None]
    supports = [r["metrics"]["support"] for r in runs if r["metrics"]["support"] is not None]
    head = [
        "# Agent case runs", "",
        f"{len(runs)} runs, model `{config.AGENT_MODEL}`, generated "
        f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.", "",
        f"- citations backed by a retrieved source: {cited - unsup}/{cited}"
        + (f" ({100 * (cited - unsup) / cited:.0f}%)" if cited else ""),
        f"- gold page retrieved (topic questions): {sum(gold)}/{len(gold)}",
        f"- mean reranker support of answer claims: "
        + (f"{sum(supports) / len(supports):.2f}" if supports else "n/a (no reranker)"), "",
    ]
    (CASES / "summary.md").write_text("\n".join(head + rows) + "\n")
    print(f"wrote {CASES / 'summary.md'}")


def main() -> None:
    if "--summary-only" not in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        n_topics = int(sys.argv[sys.argv.index("--topics") + 1]) if "--topics" in sys.argv else 8
        OUT.mkdir(parents=True, exist_ok=True)
        for cand in candidates(n_topics):
            if only and cand["slug"] not in only:
                continue
            print(f"=== {cand['slug']}: {cand['question']}", flush=True)
            start = time.time()
            try:
                out = ask(cand["question"])
            except Exception as e:
                print(f"  ERROR {e}")
                continue
            run = out | {"slug": cand["slug"], "expectation": cand["expectation"],
                         "gold_page": cand["gold_page"], "model": config.AGENT_MODEL,
                         "ran_at": datetime.now(timezone.utc).isoformat(),
                         "metrics": metrics(out, time.time() - start, cand["gold_page"])}
            (OUT / f"{cand['slug']}.json").write_text(
                json.dumps(run, indent=2, ensure_ascii=False, default=str))
            (OUT / f"{cand['slug']}.md").write_text(to_markdown(run))
            print(f"  {run['metrics']}", flush=True)
    write_summary()


if __name__ == "__main__":
    main()
