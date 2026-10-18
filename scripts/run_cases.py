"""Run candidate questions through the QA agent and save traces for case selection.

Writes docs/cases/runs/<slug>.json (full trace incl. Hermes messages) and <slug>.md
(human-readable). Pick 3 successes + 3 failures from these and annotate them in
docs/cases/README.md.

Usage: uv run python scripts/run_cases.py [--topics 8] [--only slug1,slug2]
"""

import json
import re
import sys
from datetime import datetime, timezone

from two_beefies import config
from two_beefies.qa import ask

OUT = config.ROOT / "docs" / "cases" / "runs"

# Fixed probes for known weak spots: (slug, question, what we expect to see)
PROBES = [
    ("ambiguity-mercury", "What does each source say about Mercury?",
     "failure risk: ambiguity (planet / god / metal)"),
    ("aggregate-count", "How many of the indexed Britannica pages are about medicine?",
     "failure risk: aggregate question that top-k retrieval cannot answer"),
    ("not-indexed", "What did the Britannica say about the steam locomotive?",
     "failure risk: topic probably not among the indexed pages -> should admit no evidence"),
    ("long-s-ocr", "Find Britannica passages that use the word 'such'.",
     "failure risk: long-s OCR ('fuch') breaks lexical search"),
    ("illustrations", "Which indexed Britannica pages contain illustrations, and what do they show?",
     "failure risk: needs the image, not just the OCR text"),
]
TOPIC_TEMPLATE = ("What does the Britannica say about {t}, and how does modern Wikipedia "
                  "describe it? What changed: language, knowledge or perspective?")


def candidates(n_topics: int) -> list[tuple[str, str, str]]:
    """Comparison questions for headwords that are actually indexed, plus fixed probes."""
    from two_beefies.retrieval import topics
    per_topic = [("topic-" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-"),
                  TOPIC_TEMPLATE.format(t=t),
                  "success candidate: indexed page with a Wikipedia counterpart")
                 for t in topics(n_topics)]
    return per_topic + PROBES


def to_markdown(slug: str, expectation: str, out: dict) -> str:
    lines = [f"# {slug}", "", f"**Question:** {out['question']}", "",
             f"**Expectation:** {expectation}", "", "## Tool calls", ""]
    for c in out["trace"]:
        lines.append(f"- `{c['name']}({json.dumps(c['args'], ensure_ascii=False)})` -> "
                     f"{len(c['cite_ids'])} hits")
    lines += ["", "## Answer", "", out["answer"], "", "## Citations", ""]
    for c in out["citations"]:
        lines.append(f"- `{c['cite_id']}` ({c['source']}) {c['title']}: {c['snippet'][:160]}")
    lines += ["", f"**Unsupported citation ids:** {out['unsupported'] or 'none'}", "",
              "## Verdict (fill in)", "", "- success / failure:", "- why:",
              "- what it reveals about the pipeline:", ""]
    return "\n".join(lines)


def main() -> None:
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    n_topics = int(sys.argv[sys.argv.index("--topics") + 1]) if "--topics" in sys.argv else 8
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, question, expectation in candidates(n_topics):
        if only and slug not in only:
            continue
        print(f"=== {slug}: {question}", flush=True)
        try:
            out = ask(question)
        except Exception as e:
            print(f"  ERROR {e}")
            continue
        out |= {"slug": slug, "expectation": expectation, "model": config.AGENT_MODEL,
                "ran_at": datetime.now(timezone.utc).isoformat()}
        (OUT / f"{slug}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                                     default=str))
        (OUT / f"{slug}.md").write_text(to_markdown(slug, expectation, out))
        print(re.sub(r"\s+", " ", out["answer"])[:300], "...")
        print(f"  calls={len(out['trace'])} cited={len(out['citations'])} "
              f"unsupported={out['unsupported']}", flush=True)


if __name__ == "__main__":
    main()
