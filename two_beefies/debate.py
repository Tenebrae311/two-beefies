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


def run_debate(topic: str, emit: Emit, rounds: int = 3) -> dict:
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

        intro = f"The debate topic is: {topic}.\n" if last_wp is None else ""
        msg = (f"{intro}The Britannica scholar said:\n\n{last_eb.text}\n\n"
               f"Respond from Wikipedia: what is still true, what changed, what is only "
               f"different wording? Search first.")
        last_wp = _turn(wp, rnd, msg, emit)
        transcript.append(f"[Round {rnd}] WIKIPEDIA EDITOR:\n{last_wp.text}")

        emit({"type": "turn_start", "role": "moderator", "round": rnd})
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

    emit({"type": "verdict"} | verdict)
    emit({"type": "done"})
    return {"topic": topic, "transcript": transcript, "verdict": verdict}


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
    elif t == "verdict":
        print("\n===== VERDICT =====")
        print(json.dumps({k: v for k, v in e.items() if k != "type"}, indent=2,
                         ensure_ascii=False))


if __name__ == "__main__":
    run_debate(" ".join(sys.argv[1:]) or "Astronomy", _print_event)
