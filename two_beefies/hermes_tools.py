"""Retrieval tools registered into the Hermes Agent tool registry.

Toolsets (enabled per agent role via AIAgent(enabled_toolsets=...)):
  britannica  search_britannica, read_britannica, inspect_page_image
  wikipedia   search_wikipedia, read_wikipedia
  crosswalk   find_counterparts
  vision      compare_images (needs both sources, so never given to a debater)

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

from two_beefies import retrieval, vision

log = logging.getLogger(__name__)

TOOLSETS = ("britannica", "wikipedia", "crosswalk", "vision")


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


def _record(task_id: str | None, name: str, args: dict, rows: list[dict],
            extra: dict | None = None) -> None:
    task = _tasks.get(task_id or "")
    if task is None:
        return
    cits = [retrieval.to_citation(r) for r in rows]
    for c in cits:
        task.retrieved[c["cite_id"]] = c
    task.calls.append({"name": name, "args": args, "n_hits": len(rows),
                       "cite_ids": [c["cite_id"] for c in cits]} | (extra or {}))
    if task.on_event:
        task.on_event({"type": "tool_result", "role": task.role, "name": name, "hits": cits}
                      | (extra or {}))


def _compact(row: dict) -> dict:
    """What the model sees for a search hit: provenance + snippet, no vectors."""
    keys = ("cite_id", "title", "section", "edition", "volume_label", "page_index", "illustrated",
            "date_modified", "retrieval_score", "rerank_score")
    out = {k: row[k] for k in keys if row.get(k) is not None}
    if row["source"] == "wikipedia" and row.get("image_url"):
        out["has_image"] = True
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


def _inspect_handler(args: dict, task_id: str | None = None, **_) -> str:
    try:
        cite_id, question = str(args.get("cite_id", "")), str(args.get("question", ""))
        if retrieval.parse_cite_id(cite_id)[0] != "britannica":
            return json.dumps({"error": "inspect_page_image only works on Britannica scans"})
        row = retrieval.get(cite_id)
        if row is None:
            return json.dumps({"error": f"Unknown cite_id {cite_id}"})
        answer = vision.inspect_page(row, question)
        _record(task_id, "inspect_page_image", args, [row], {"vision": {
            "question": question, "answer": answer, "images": [row.get("image_url")]}})
        return json.dumps({"cite_id": row["cite_id"], "edition": row.get("edition"),
                           "seen_on_scan": answer}, ensure_ascii=False)
    except Exception as e:
        return _err(e)


def _compare_handler(args: dict, task_id: str | None = None, **_) -> str:
    try:
        eb = retrieval.get(str(args.get("britannica_cite_id", "")))
        wp = retrieval.get(str(args.get("wikipedia_cite_id", "")))
        if eb is None or wp is None or eb["source"] != "britannica" or wp["source"] != "wikipedia":
            return json.dumps({"error": "need one Britannica and one Wikipedia cite_id"})
        question = str(args.get("question", ""))
        answer = vision.compare(eb, wp, question)
        _record(task_id, "compare_images", args, [eb, wp], {"vision": {
            "question": question, "answer": answer,
            "images": [eb.get("image_url"), wp.get("image_url")]}})
        return json.dumps({"britannica": eb["cite_id"], "wikipedia": wp["cite_id"],
                           "comparison": answer}, ensure_ascii=False)
    except Exception as e:
        return _err(e)


def _counterparts_handler(args: dict, task_id: str | None = None, **_) -> str:
    try:
        matches = retrieval.counterparts(str(args.get("britannica_cite_id", "")))
        task = _tasks.get(task_id or "")
        if task is not None:
            task.calls.append({"name": "find_counterparts", "args": args,
                               "n_hits": len(matches),
                               "cite_ids": [m["wikipedia_cite_id"] for m in matches
                                            if m.get("wikipedia_cite_id")]})
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
        name="inspect_page_image", toolset="britannica",
        schema=_schema("inspect_page_image",
                       "Look at the ORIGINAL SCAN of a Britannica page with the vision model. "
                       "Use it when the OCR text is garbled or incomplete, to check a word or "
                       "number, or to describe an engraving/illustration (pages marked "
                       "illustrated). Returns what is visible on the scan.",
                       {"cite_id": _CITE,
                        "question": {"type": "string",
                                     "description": "What to look for on the page."}},
                       ["cite_id", "question"]),
        handler=_inspect_handler)
    registry.register(
        name="compare_images", toolset="vision",
        schema=_schema("compare_images",
                       "Compare a Britannica page scan (e.g. an 18th-century engraving) with "
                       "the lead image of a Wikipedia article (results marked has_image) using "
                       "the vision model: how did the depiction of the subject change?",
                       {"britannica_cite_id": _CITE,
                        "wikipedia_cite_id": {"type": "string",
                                              "description": "Wikipedia citation id, e.g. 'WP:123-0'."},
                        "question": {"type": "string", "description": "What to compare."}},
                       ["britannica_cite_id", "wikipedia_cite_id", "question"]),
        handler=_compare_handler)
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
                       "Look up the precomputed closest Wikipedia passage for a Britannica "
                       "passage, with its cosine score and a no_clear_match flag (page-level fallback for older data).",
                       {"britannica_cite_id": _CITE}, ["britannica_cite_id"]),
        handler=_counterparts_handler)
