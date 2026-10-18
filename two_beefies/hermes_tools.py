"""Retrieval tools registered into the Hermes Agent tool registry.

Toolsets (enabled per agent role via AIAgent(enabled_toolsets=...)):
  britannica  search_britannica, read_britannica
  wikipedia   search_wikipedia, read_wikipedia
  crosswalk   find_counterparts

Every handler records which citation ids it handed to the model, keyed by the Hermes
task_id. `grounding.py` later checks the agent's answer against that record, and the
optional per-task event sink streams tool activity to the frontend.
"""

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from tools.registry import registry

from two_beefies import retrieval

log = logging.getLogger(__name__)

TOOLSETS = ("britannica", "wikipedia", "crosswalk")


@dataclass
class TaskLog:
    role: str
    on_event: Callable[[dict], None] | None = None
    retrieved: dict[str, dict] = field(default_factory=dict)  # cite_id -> citation
    calls: list[dict] = field(default_factory=list)  # {name, args, n_hits}


_tasks: dict[str, TaskLog] = {}
_lock = threading.Lock()


def start_task(task_id: str, role: str, on_event: Callable[[dict], None] | None = None) -> TaskLog:
    with _lock:
        _tasks[task_id] = TaskLog(role=role, on_event=on_event)
        return _tasks[task_id]


def end_task(task_id: str) -> TaskLog | None:
    with _lock:
        return _tasks.pop(task_id, None)


def _record(task_id: str | None, name: str, args: dict, rows: list[dict]) -> None:
    task = _tasks.get(task_id or "")
    if task is None:
        return
    cits = [retrieval.to_citation(r) for r in rows]
    for c in cits:
        task.retrieved[c["cite_id"]] = c
    task.calls.append({"name": name, "args": args, "n_hits": len(rows),
                       "cite_ids": [c["cite_id"] for c in cits]})
    if task.on_event:
        task.on_event({"type": "tool_result", "role": task.role, "name": name, "hits": cits})


def _compact(row: dict) -> dict:
    """What the model sees for a search hit: provenance + snippet, no vectors."""
    keys = ("cite_id", "title", "section", "edition", "year", "volume_label", "page_seq",
            "date_modified", "retrieval_score", "rerank_score")
    out = {k: row[k] for k in keys if row.get(k) is not None}
    out["snippet"] = retrieval.snippet(row.get("text", ""))
    return out


def _err(e: Exception) -> str:
    log.exception("tool failed")
    return json.dumps({"error": f"{type(e).__name__}: {e}"})


def _search_handler(source: retrieval.Source, name: str):
    def handler(args: dict, task_id: str | None = None, **_) -> str:
        try:
            query = str(args.get("query", "")).strip()
            if not query:
                return json.dumps({"error": "query must not be empty"})
            k = max(1, min(int(args.get("k", 5)), 10))
            rows = retrieval.search(source, query, k=k, edition=args.get("edition"))
            _record(task_id, name, args, rows)
            if not rows:
                return json.dumps({"results": [], "note": "No matching passages found."})
            return json.dumps({"results": [_compact(r) for r in rows]}, ensure_ascii=False,
                              default=str)
        except Exception as e:
            return _err(e)
    return handler


def _read_handler(source: retrieval.Source, name: str):
    def handler(args: dict, task_id: str | None = None, **_) -> str:
        try:
            cite_id = str(args.get("cite_id", ""))
            src, _ = retrieval.parse_cite_id(cite_id)
            if src != source:
                return json.dumps({"error": f"{name} can only read {source} sources"})
            row = retrieval.get(cite_id)
            if row is None:
                return json.dumps({"error": f"Unknown cite_id {cite_id}"})
            _record(task_id, name, args, [row])
            out = _compact(row) | {"text": row.get("text", "")[:6000], "url": row.get("url")}
            out.pop("snippet")
            return json.dumps(out, ensure_ascii=False, default=str)
        except Exception as e:
            return _err(e)
    return handler


def _counterparts_handler(args: dict, task_id: str | None = None, **_) -> str:
    try:
        matches = retrieval.counterparts(str(args.get("britannica_cite_id", "")))
        if not matches:
            return json.dumps({"matches": [], "note": "No precomputed match for this page."})
        return json.dumps({"matches": matches}, ensure_ascii=False, default=str)
    except Exception as e:
        return _err(e)


def _schema(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}


_QUERY = {"type": "string", "description": "Search query in English. Use modern spelling; "
          "also try historical spellings or synonyms if the first search finds nothing."}
_K = {"type": "integer", "description": "Number of passages to return (1-10, default 5)."}
_CITE = {"type": "string", "description": "Citation id from a search result, e.g. 'EB:123'."}

_registered = False


def register() -> None:
    global _registered
    if _registered:
        return
    _registered = True
    registry.register(
        name="search_britannica", toolset="britannica",
        schema=_schema("search_britannica",
                       "Search historical Encyclopaedia Britannica pages (editions 1-8, "
                       "1768-1860, OCR text of scanned pages). Returns passages with citation ids.",
                       {"query": _QUERY, "k": _K,
                        "edition": {"type": "string",
                                    "description": "Optional edition filter, e.g. '1st', '7th'."}},
                       ["query"]),
        handler=_search_handler("britannica", "search_britannica"))
    registry.register(
        name="read_britannica", toolset="britannica",
        schema=_schema("read_britannica", "Read the full text of a Britannica passage by citation id.",
                       {"cite_id": _CITE}, ["cite_id"]),
        handler=_read_handler("britannica", "read_britannica"))
    registry.register(
        name="search_wikipedia", toolset="wikipedia",
        schema=_schema("search_wikipedia",
                       "Search modern English Wikipedia articles (Wikimedia Structured Contents "
                       "snapshot). Returns passages with citation ids.",
                       {"query": _QUERY, "k": _K}, ["query"]),
        handler=_search_handler("wikipedia", "search_wikipedia"))
    registry.register(
        name="read_wikipedia", toolset="wikipedia",
        schema=_schema("read_wikipedia", "Read the full text of a Wikipedia passage by citation id.",
                       {"cite_id": _CITE}, ["cite_id"]),
        handler=_read_handler("wikipedia", "read_wikipedia"))
    registry.register(
        name="find_counterparts", toolset="crosswalk",
        schema=_schema("find_counterparts",
                       "Look up the precomputed best-matching Wikipedia articles for a Britannica "
                       "page (from the matching pipeline), with scores and a no_clear_match flag.",
                       {"britannica_cite_id": _CITE}, ["britannica_cite_id"]),
        handler=_counterparts_handler)
