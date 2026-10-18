"""Run candidate questions through the QA agent and save traces for case selection.

Writes docs/cases/runs/<slug>.json (full trace incl. Hermes messages) and <slug>.md
(human-readable). Pick 3 successes + 3 failures from these and annotate them in
docs/cases/README.md.

Usage: uv run python scripts/run_cases.py [--only slug1,slug2]
"""

import json
import re
import sys
from datetime import datetime, timezone

from two_beefies import config
from two_beefies.qa import ask

OUT = config.ROOT / "docs" / "cases" / "runs"

# (slug, question, what we expect to see)
CANDIDATES = [
    ("planets", "How many planets did the 1771 Britannica describe, and how does that compare "
     "with modern Wikipedia?", "success: clear knowledge change (Uranus 1781, Neptune 1846)"),
    ("copernican", "Does the Britannica accept that the Earth moves around the Sun? How does "
     "Wikipedia describe the same idea?", "success: agreement, mostly language change"),
    ("blood", "What did the Britannica say about blood and its circulation, and what has "
     "changed according to Wikipedia?", "success: knowledge change (cells, oxygen)"),
    ("bloodletting", "Was bloodletting recommended as a treatment in the Britannica? What does "
     "Wikipedia say about it today?", "success: knowledge + perspective change"),
    ("africa", "How does the Britannica describe Africa and its inhabitants compared with "
     "Wikipedia?", "perspective change; risk of thin evidence"),
    ("bee", "What did the Britannica know about how bees reproduce?", "knowledge change"),
    ("air", "What is air made of, according to each source?", "knowledge change "
     "(pre-oxygen 1771); OCR 'fpring'"),
    ("mercury", "What does each source say about Mercury?", "failure: ambiguity "
     "(planet / god / metal)"),
    ("ocr-such", "Find Britannica passages that use the word 'such' about the stars.",
     "failure: long-s OCR ('fuch')"),
    ("count", "How many articles in the 1771 Britannica volume are about medicine?",
     "failure: aggregate question retrieval cannot answer"),
    ("electricity", "What did the Britannica say about electricity?", "failure: not in "
     "the A-B fixture volume -> should admit no evidence"),
    ("abyssinia", "How did the Britannica describe Abyssinia, and what is its modern "
     "counterpart?", "no clear counterpart / renamed entity"),
]


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
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, question, expectation in CANDIDATES:
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
