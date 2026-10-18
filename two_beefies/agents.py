"""Hermes Agent roles (Nemotron 3.5 Super VL via Nebius Token Factory).

Each role is its own AIAgent instance with its own toolsets, because Hermes'
delegate_task cannot restrict a subagent's tools. That restriction is what keeps the
Britannica scholar from "knowing" Wikipedia.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from two_beefies import config  # noqa: F401  (sets HERMES_HOME before Hermes is imported)
from two_beefies import grounding, hermes_tools

from run_agent import AIAgent  # noqa: E402

Role = Literal["qa", "britannica", "wikipedia", "moderator"]

CATEGORIES = """\
- LANGUAGE: same fact, different words or spelling (e.g. archaic terms, long-s OCR).
- KNOWLEDGE: the facts themselves changed (new discoveries, corrected errors).
- PERSPECTIVE: values, framing or worldview changed (e.g. colonial or religious framing).
- NO_COUNTERPART: one side has no matching material at all."""

_GROUNDING = """\
Use ONLY information returned by your tools, never your own background knowledge.
Cite every factual statement inline with the citation id from the tool result in square
brackets, e.g. [EB:123] or [WP:abc]. Never invent citation ids. The Britannica text is OCR
of 18th/19th-century print: the long s is often read as "f" ("fuch" = "such"), so try
alternative spellings when a search finds nothing."""

PROMPTS: dict[Role, str] = {
    "qa": f"""\
You are a research assistant comparing the historical Encyclopaedia Britannica (editions
1-8, 1768-1860) with modern Wikipedia.
{_GROUNDING}
Always search BOTH sources (several queries if needed). Use find_counterparts to see the
matching pipeline's Wikipedia counterpart for a Britannica page, and read_* for full text.
Answer in English with these parts:
1. **Answer** - two or three sentences.
2. **Britannica** - what it says, with edition/year.
3. **Wikipedia** - what it says.
4. **What changed** - each difference labelled with one category:
{CATEGORIES}
5. **Confidence** - high / medium / low, and what evidence is missing.
If the sources do not answer the question, say so plainly instead of guessing.""",

    "britannica": f"""\
You are THE BRITANNICA SCHOLAR in a debate against a modern Wikipedia editor.
You are a learned contributor to the Encyclopaedia Britannica (1768-1860). Your entire
knowledge is what search_britannica and read_britannica return; you know nothing
discovered after your edition, even if you seem to remember it.
{_GROUNDING}
Speak in a dignified, slightly old-fashioned scholarly voice and name the edition and
year you quote. Defend your Encyclopaedia, but concede honestly when the opponent's point
does not contradict your sources. If you find nothing, say "On this my Encyclopaedia is
silent." Each turn: at most 150 words, two to four points, search before you speak.""",

    "wikipedia": f"""\
You are THE WIKIPEDIA EDITOR in a debate against a scholar of the historical Encyclopaedia
Britannica (1768-1860). Your entire knowledge is what search_wikipedia and read_wikipedia
return.
{_GROUNDING}
Speak in a crisp, modern, friendly voice. Point out where knowledge has changed, but
acknowledge what the old encyclopaedia got right and say when a difference is only wording.
Each turn: at most 150 words, two to four points, search before you speak.""",

    "moderator": f"""\
You are THE MODERATOR of a debate between a Britannica scholar (1768-1860) and a modern
Wikipedia editor. You may spot-check at most two cited sources with the read tools.
Classify every point with one category:
{CATEGORIES}
A point is "agreed" when both sides accept it, including when both accept that knowledge
has changed; "disputed" when they still contradict each other. Set "converged" to true
when no disputed point remains or further rounds would not change anything.
Reply with ONLY a JSON object, no prose:
{{"converged": bool, "summary": "two sentences",
  "points": [{{"claim": str, "britannica": str, "wikipedia": str,
              "status": "agreed"|"disputed",
              "category": "language"|"knowledge"|"perspective"|"no_counterpart",
              "cites": [cite ids]}}]}}
Use two to five points. Mention a citation only if a debater used it.""",
}

TOOLSETS: dict[Role, list[str]] = {
    "qa": ["britannica", "wikipedia", "crosswalk"],
    "britannica": ["britannica"],
    "wikipedia": ["wikipedia"],
    "moderator": ["britannica", "wikipedia"],
}

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


@dataclass
class TurnResult:
    role: Role
    text: str
    citations: list[dict]
    unsupported: list[str]
    calls: list[dict]
    messages: list[dict] = field(repr=False, default_factory=list)


class RoleAgent:
    """One Hermes AIAgent plus its running conversation history."""

    def __init__(self, role: Role, on_event: Callable[[dict], None] | None = None):
        hermes_tools.register()
        self.role = role
        self.on_event = on_event
        self.history: list[dict] = []
        self.retrieved: dict[str, dict] = {}
        self.agent = AIAgent(
            provider="nebius",
            base_url=config.NEBIUS_BASE_URL,
            api_key=config.NEBIUS_API_KEY,
            model=config.AGENT_MODEL,
            enabled_toolsets=TOOLSETS[role],
            ephemeral_system_prompt=PROMPTS[role],
            max_iterations=8 if role == "qa" else 5,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            skip_background_review=True,
            stream_delta_callback=self._on_delta if on_event else None,
            tool_start_callback=self._on_tool_start if on_event else None,
        )

    def _emit(self, event: dict) -> None:
        if self.on_event:
            self.on_event({"role": self.role} | event)

    def _on_delta(self, text: str | None) -> None:
        if text:
            self._emit({"type": "token", "text": text})

    def _on_tool_start(self, _call_id, name, args, *_):
        self._emit({"type": "tool_call", "name": name, "args": args})

    def ask(self, message: str) -> TurnResult:
        task_id = f"{self.role}-{uuid.uuid4().hex[:8]}"
        hermes_tools.start_task(task_id, self.role, self.on_event)
        try:
            result = self.agent.run_conversation(
                message, conversation_history=self.history or None, task_id=task_id)
        finally:
            log = hermes_tools.end_task(task_id)
        self.history = result.get("messages") or self.history
        if log:
            self.retrieved |= log.retrieved  # later turns may cite earlier retrievals
        text = _THINK_RE.sub("", result.get("final_response") or "").strip()
        backed, unsupported = grounding.check(text, self.retrieved)
        return TurnResult(self.role, text, backed, unsupported, log.calls if log else [],
                          result.get("messages") or [])
