"""Debate mode: Britannica scholar vs. Wikipedia editor, judged by a moderator.

Turn order per round: Britannica, Wikipedia (each answering the other's last turn),
then the moderator classifies the points. Stops when the moderator reports convergence
or after `rounds` rounds. All events follow the backend <-> frontend contract
(see frontend/README.md).
"""

import json
import re
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from two_beefies import config, evidence
from two_beefies.agents import RoleAgent, TurnResult

Emit = Callable[[dict], None]

_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_verdict(text: str) -> dict:
    match = _JSON_RE.search(text or "")
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    points = [p for p in data.get("points", []) if isinstance(p, dict)]
    for p in points:
        p["status"] = "agreed" if p.get("status") == "agreed" else "disputed"
        p["category"] = str(p.get("category", "knowledge")).lower()
        p.setdefault("cites", [])
    return {
        "converged": bool(data.get("converged", False)),
        "summary": data.get("summary") or (text if not data else ""),
        "points": points,
    }


def _turn(agent: RoleAgent, rnd: int, message: str, emit: Emit) -> TurnResult:
    emit({"type": "turn_start", "role": agent.role, "round": rnd})
    turn = agent.ask(message)
    emit({"type": "turn_end", "role": agent.role, "round": rnd, "text": turn.text,
          "citations": turn.citations, "unsupported": turn.unsupported})
    return turn


def _check_evidence(agent: RoleAgent, turn: TurnResult, rnd: int, emit: Emit,
                    anachronisms: list[dict], supports: dict[str, list[float]]) -> str:
    """Score the turn with the reranker; returns a note for the moderator's transcript."""
    ev = evidence.score_turn(agent.role, turn.text, agent.retrieved)
    if ev is None:  # no reranker configured: the UI shows "reranker offline"
        emit({"type": "evidence", "role": agent.role, "round": rnd, "support": None,
              "claims": []})
        return ""
    emit({"type": "evidence", "role": agent.role, "round": rnd} | ev)
    if ev["support"] is not None:
        supports[agent.role].append(ev["support"])
    flagged = [c for c in ev["claims"] if c["flag"] in ("anachronism", "unsupported")]
    for c in flagged:
        if c["flag"] == "anachronism":
            anachronisms.append({"round": rnd, "text": c["text"], "support": c["support"],
                                 "modern_support": c["modern_support"]})
    if not flagged:
        return ""
    lines = [f"- {c['flag'].upper()}: \"{c['text']}\" (own sources {c['support']}, "
             f"Wikipedia {c['modern_support']})" for c in flagged]
    return "[Reranker evidence check of this turn]\n" + "\n".join(lines)


def _record_events(topic: str, emit: Emit) -> tuple[Emit, Path]:
    """Also write every event to data/debates/ (replays for the demo, evidence for the docs)."""
    out = config.ROOT / "data" / "debates"
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40]
    path = out / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}.jsonl"

    def recording_emit(event: dict) -> None:
        if event["type"] != "token":
            with path.open("a") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        emit(event)
    return recording_emit, path


def run_debate(topic: str, emit: Emit, rounds: int = 3) -> dict:
    emit, log_path = _record_events(topic, emit)
    anachronisms: list[dict] = []
    supports: dict[str, list[float]] = {"britannica": [], "wikipedia": []}
    eb = RoleAgent("britannica", emit)
    wp = RoleAgent("wikipedia", emit)
    mod = RoleAgent("moderator", emit)
    transcript: list[str] = []
    verdict = {"converged": False, "summary": "", "points": []}
    last_wp: TurnResult | None = None

    for rnd in range(1, rounds + 1):
        if last_wp is None:
            msg = (f"The debate topic is: {topic}.\nGive your opening statement: what does "
                   f"your Encyclopaedia say about it? Search first.")
        else:
            msg = (f"The Wikipedia editor replied:\n\n{last_wp.text}\n\n"
                   f"Respond: which points do you concede, which do you dispute, and why?")
        last_eb = _turn(eb, rnd, msg, emit)
        transcript.append(f"[Round {rnd}] BRITANNICA SCHOLAR:\n{last_eb.text}")
        if note := _check_evidence(eb, last_eb, rnd, emit, anachronisms, supports):
            transcript.append(note)

        intro = f"The debate topic is: {topic}.\n" if last_wp is None else ""
        msg = (f"{intro}The Britannica scholar said:\n\n{last_eb.text}\n\n"
               f"Respond from Wikipedia: what is still true, what changed, what is only "
               f"different wording? Search first.")
        last_wp = _turn(wp, rnd, msg, emit)
        transcript.append(f"[Round {rnd}] WIKIPEDIA EDITOR:\n{last_wp.text}")
        if note := _check_evidence(wp, last_wp, rnd, emit, anachronisms, supports):
            transcript.append(note)

        emit({"type": "turn_start", "role": "moderator", "round": rnd})
        # The moderator judges the debaters' evidence, so their retrievals count as backed.
        mod.retrieved |= eb.retrieved | wp.retrieved
        mod_turn = mod.ask(
            f"Topic: {topic}\nRound {rnd} of at most {rounds}. Full transcript so far:\n\n"
            + "\n\n".join(transcript))
        verdict = parse_verdict(mod_turn.text)
        # The frontend parses the moderator's text as the ruling JSON.
        emit({"type": "turn_end", "role": "moderator", "round": rnd,
              "text": json.dumps(verdict, ensure_ascii=False),
              "citations": mod_turn.citations, "unsupported": mod_turn.unsupported})
        if verdict["converged"]:
            break

    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
    verdict["evidence"] = {"britannica": mean(supports["britannica"]),
                           "wikipedia": mean(supports["wikipedia"]),
                           "anachronisms": anachronisms}
    emit({"type": "verdict"} | verdict)
    emit({"type": "done"})
    return {"topic": topic, "transcript": transcript, "verdict": verdict, "log": str(log_path)}


def _print_event(e: dict) -> None:
    t = e["type"]
    if t == "turn_start":
        print(f"\n===== {e['role'].upper()} (round {e['round']}) =====", flush=True)
    elif t == "tool_call":
        print(f"  > {e['name']}({json.dumps(e['args'], ensure_ascii=False)})", flush=True)
    elif t == "turn_end":
        print(e["text"] if e["role"] != "moderator" else json.loads(e["text"])["summary"])
        if e.get("unsupported"):
            print(f"  !! unsupported citations: {e['unsupported']}")
    elif t == "evidence":
        print(f"  [evidence] mean support {e['support']}")
        for c in e["claims"]:
            if c["flag"] != "supported":
                print(f"    {c['flag']:<12} own={c['support']} modern={c['modern_support']} | "
                      f"{c['text'][:90]}")
    elif t == "verdict":
        print("\n===== VERDICT =====")
        print(json.dumps({k: v for k, v in e.items() if k != "type"}, indent=2,
                         ensure_ascii=False))


if __name__ == "__main__":
    run_debate(" ".join(sys.argv[1:]) or "Astronomy", _print_event)
