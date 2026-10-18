"""Retrieval over the two LanceDB tables: Nemotron embed -> LanceDB -> Nemotron rerank.

Falls back to LanceDB full-text search when no embedding endpoint is configured, and to
the raw vector/FTS order when no reranker is configured, so the agent keeps working
while the NIM containers are not up yet.
"""

import json
import logging
import sys
from functools import cache
from typing import Literal

import httpx
import lancedb
from lancedb.index import FTS

from two_beefies import config

log = logging.getLogger(__name__)

Source = Literal["britannica", "wikipedia"]
PREFIX = {"britannica": "EB", "wikipedia": "WP"}
TABLES = {"britannica": config.BRITANNICA_TABLE, "wikipedia": config.WIKIPEDIA_TABLE}


@cache
def _db():
    return lancedb.connect(config.LANCEDB_URI)


@cache
def _table(source: Source):
    return _db().open_table(TABLES[source])


def _nim_url(base: str, path: str) -> str:
    return base if base.endswith(path) else f"{base}/v1/{path}"


def _nim_headers() -> dict:
    return {"Authorization": f"Bearer {config.NIM_API_KEY}"} if config.NIM_API_KEY else {}


def embed_query(text: str) -> list[float]:
    resp = httpx.post(
        _nim_url(config.EMBED_URL, "embeddings"),
        headers=_nim_headers(),
        json={"model": config.EMBED_MODEL, "input": [text], "input_type": "query",
              "modality": "text", "encoding_format": "float", "truncate": "END"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def rerank(query: str, passages: list[str]) -> list[tuple[int, float]]:
    """Return (passage index, logit) sorted best first."""
    resp = httpx.post(
        _nim_url(config.RERANK_URL, "ranking"),
        headers=_nim_headers(),
        json={"model": config.RERANK_MODEL, "query": {"text": query},
              "passages": [{"text": p} for p in passages], "truncate": "END"},
        timeout=60,
    )
    resp.raise_for_status()
    return [(r["index"], r["logit"]) for r in resp.json()["rankings"]]


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _candidates(source: Source, query: str, n: int, where: str | None) -> list[dict]:
    tbl = _table(source)
    if config.EMBED_URL:
        q = tbl.search(embed_query(query)).distance_type("cosine")
    else:
        try:
            q = tbl.search(query, query_type="fts")
        except Exception:  # no FTS index yet
            tbl.create_index("text", config=FTS(), replace=True)
            q = tbl.search(query, query_type="fts")
    if where:
        q = q.where(where, prefilter=True)
    return q.limit(n).to_list()


def _score(row: dict) -> float | None:
    if "_distance" in row:
        return round(1 - row["_distance"], 4)
    if "_score" in row:
        return round(row["_score"], 4)
    return None


def search(source: Source, query: str, k: int = 5, edition: str | None = None) -> list[dict]:
    where = f"edition = {_quote(edition)}" if edition and source == "britannica" else None
    rows = _candidates(source, query, config.CANDIDATES if config.RERANK_URL else k, where)
    for row in rows:
        row["retrieval_score"] = _score(row)
    if config.RERANK_URL and rows:
        ranked = rerank(query, [r["text"][:4000] for r in rows])
        rows = [rows[i] | {"rerank_score": round(logit, 3)} for i, logit in ranked]
    return [_clean(source, r) for r in rows[:k]]


def _clean(source: Source, row: dict) -> dict:
    row = {k: v for k, v in row.items() if k != "vector" and not k.startswith("_")}
    row["source"] = source
    row["cite_id"] = f"{PREFIX[source]}:{row['id']}"
    return row


def parse_cite_id(cite_id: str) -> tuple[Source, str]:
    prefix, _, row_id = cite_id.strip().strip("[]").partition(":")
    source = {"EB": "britannica", "WP": "wikipedia"}.get(prefix.upper())
    if not source or not row_id:
        raise ValueError(f"Not a citation id: {cite_id!r} (expected EB:<id> or WP:<id>)")
    return source, row_id


def get(cite_id: str) -> dict | None:
    source, row_id = parse_cite_id(cite_id)
    rows = _table(source).search().where(f"id = {_quote(row_id)}").limit(1).to_list()
    return _clean(source, rows[0]) if rows else None


def counterparts(cite_id: str) -> list[dict]:
    """Team 1's Britannica -> Wikipedia matches for the page this chunk belongs to."""
    row = get(cite_id)
    if row is None or row["source"] != "britannica":
        return []
    try:
        matches = _db().open_table(config.MATCHES_TABLE)
    except Exception as e:
        log.warning("matches table unavailable: %s", e)
        return []
    found = (matches.search().where(f"britannica_doc_id = {_quote(row['doc_id'])}")
             .limit(10).to_list())
    out = []
    for m in sorted(found, key=lambda m: m.get("rank", 0)):
        m = {k: v for k, v in m.items() if not k.startswith("_")}
        if m.get("wikipedia_doc_id"):
            wp = (_table("wikipedia").search()
                  .where(f"doc_id = {_quote(str(m['wikipedia_doc_id']))}").limit(1).to_list())
            if wp:
                m["wikipedia_title"] = wp[0]["title"]
                m["wikipedia_cite_id"] = f"WP:{wp[0]['id']}"
        out.append(m)
    return out


def snippet(text: str, n: int = config.SNIPPET_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"


def to_citation(row: dict, full_text: bool = False) -> dict:
    """Citation shape of the backend <-> frontend event contract."""
    cit = {
        "cite_id": row["cite_id"],
        "source": row["source"],
        "title": row.get("title") or row.get("volume_label") or row["doc_id"],
        "snippet": snippet(row.get("text", ""), 300),
        "url": row.get("url"),
        "image_url": row.get("image_url"),
        "edition": row.get("edition"),
        "year": row.get("year"),
    }
    if full_text:
        cit["text"] = row.get("text", "")
    return cit


if __name__ == "__main__":
    src, query = sys.argv[1], " ".join(sys.argv[2:])
    for hit in search(src, query):
        hit["text"] = snippet(hit["text"], 200)
        print(json.dumps(hit, ensure_ascii=False, default=str))
