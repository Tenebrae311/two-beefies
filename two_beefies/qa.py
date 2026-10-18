"""Single-question mode: one Hermes agent with access to both sources."""

import json
import sys

from two_beefies import evidence
from two_beefies.agents import RoleAgent


def ask(question: str) -> dict:
    agent = RoleAgent("qa")
    turn = agent.ask(question)
    return {
        "question": question,
        "answer": turn.text,
        "citations": turn.citations,
        "unsupported": turn.unsupported,
        "trace": turn.calls,
        "evidence": evidence.score_turn("qa", turn.text, agent.retrieved),
        "messages": turn.messages,
    }


if __name__ == "__main__":
    out = ask(" ".join(sys.argv[1:]))
    print(out["answer"])
    print("\n--- tool calls")
    for c in out["trace"]:
        print(f"{c['name']}({json.dumps(c['args'], ensure_ascii=False)}) -> {c['cite_ids']}")
    print(f"\n--- cited & retrieved: {[c['cite_id'] for c in out['citations']]}")
    print(f"--- UNSUPPORTED: {out['unsupported']}")
