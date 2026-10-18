"""Disk-backed lexical retrieval over Kaggle's English Structured Wikipedia dump."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import pyarrow.parquet as pq

INDEX_VERSION = "1"
COLUMNS = ["identifier", "name", "url", "description", "abstract", "sections",
           "version", "main_entity", "date_modified"]
SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE shards (path TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, rows INTEGER NOT NULL);
CREATE TABLE articles (
    id INTEGER PRIMARY KEY, doc_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    url TEXT NOT NULL, description TEXT NOT NULL, abstract TEXT NOT NULL,
    body TEXT NOT NULL, revision_id INTEGER NOT NULL, wikidata_qid TEXT,
    date_modified TEXT, source_file TEXT NOT NULL, source_row INTEGER NOT NULL
);
CREATE VIRTUAL TABLE article_fts USING fts5(
    title, description, abstract, body, content='articles', content_rowid='id',
    tokenize='porter unicode61 remove_diacritics 2'
);
CREATE TRIGGER articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO article_fts(rowid,title,description,abstract,body)
    VALUES (new.id,new.title,new.description,new.abstract,new.body);
END;
CREATE TRIGGER articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO article_fts(article_fts,rowid,title,description,abstract,body)
    VALUES ('delete',old.id,old.title,old.description,old.abstract,old.body);
END;
CREATE TRIGGER articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO article_fts(article_fts,rowid,title,description,abstract,body)
    VALUES ('delete',old.id,old.title,old.description,old.abstract,old.body);
    INSERT INTO article_fts(rowid,title,description,abstract,body)
    VALUES (new.id,new.title,new.description,new.abstract,new.body);
END;
CREATE INDEX article_title ON articles(title COLLATE NOCASE);
"""


def section_text(value) -> str:
    """Decode JSON-encoded sections, preserving prose/headings but not link metadata."""
    if isinstance(value, str):
        value = json.loads(value) if value.strip() else []
    if isinstance(value, list):
        return "\n\n".join(filter(None, (section_text(item) for item in value)))
    if isinstance(value, dict):
        parts = []
        if isinstance(value.get("name"), str):
            parts.append(value["name"])
        if isinstance(value.get("value"), str):
            parts.append(value["value"])
        if value.get("has_parts"):
            parts.append(section_text(value["has_parts"]))
        return "\n\n".join(filter(None, parts))
    return ""


def normalize_article(row: dict, source_file: str, source_row: int) -> dict | None:
    if urlparse(row.get("url") or "").hostname != "en.wikipedia.org":
        return None
    if row.get("identifier") is None or not row.get("name"):
        raise ValueError(f"Article without identifier/name at {source_file}:{source_row}")
    abstract = row.get("abstract") or ""
    body = section_text(row.get("sections"))
    if not body:
        body = abstract
    elif abstract and abstract not in body:
        body = abstract + "\n\n" + body
    version = row.get("version") or {}
    entity = row.get("main_entity") or {}
    return {"doc_id": str(row["identifier"]), "title": row["name"], "url": row["url"],
            "description": row.get("description") or "", "abstract": abstract, "body": body,
            "revision_id": int(version.get("identifier") or 0),
            "wikidata_qid": entity.get("identifier"),
            "date_modified": str(row["date_modified"]) if row.get("date_modified") else None,
            "source_file": source_file, "source_row": source_row}


def build_index(source: Path, index_path: Path, resume: bool = False) -> dict:
    if source.is_file():
        files = [source] if source.suffix == ".parquet" else []
    else:
        files = sorted(source.rglob("*.parquet"))
        english = [p for p in files if p.name.startswith("enwiki_namespace_0")]
        if english:
            files = english
    if not files:
        raise ValueError("No Structured Wikipedia Parquet files found")
    if index_path.exists() and not resume:
        raise ValueError("Index already exists; use --resume or a new --index path")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(index_path)
    try:
        exists = connection.execute("SELECT name FROM sqlite_master WHERE name='metadata'").fetchone()
        if not exists:
            connection.executescript(SCHEMA)
            connection.execute("INSERT INTO metadata VALUES ('version', ?)", (INDEX_VERSION,))
        elif connection.execute("SELECT value FROM metadata WHERE key='version'").fetchone()[0] != INDEX_VERSION:
            raise ValueError("Unsupported Wikipedia index version")
        previous = dict(connection.execute("SELECT path,fingerprint FROM shards"))
        fingerprints = {}
        for file in files:
            stat = file.stat()
            fingerprints[str(file.resolve())] = f"{stat.st_size}:{stat.st_mtime_ns}"
        if any(path not in fingerprints or fingerprints[path] != fp for path, fp in previous.items()):
            raise ValueError("Previously indexed shards changed/disappeared; build a fresh index")
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('ready','0')")
        connection.commit()
        for file in files:
            key = str(file.resolve())
            if key in previous:
                continue
            parquet = pq.ParquetFile(file)
            missing = {"identifier", "name", "url"} - set(parquet.schema_arrow.names)
            if missing:
                raise ValueError(f"Wrong Wikipedia schema in {file}: missing {sorted(missing)}")
            columns = [c for c in COLUMNS if c in parquet.schema_arrow.names]
            count = 0
            # A shard is one transaction: resuming never sees a half-imported shard.
            with connection:
                for batch in parquet.iter_batches(batch_size=512, columns=columns):
                    articles = []
                    for row in batch.to_pylist():
                        article = normalize_article(row, key, count)
                        count += 1
                        if article:
                            articles.append(article)
                    connection.executemany("""
                        INSERT INTO articles(doc_id,title,url,description,abstract,body,
                            revision_id,wikidata_qid,date_modified,source_file,source_row)
                        VALUES (:doc_id,:title,:url,:description,:abstract,:body,
                            :revision_id,:wikidata_qid,:date_modified,:source_file,:source_row)
                        ON CONFLICT(doc_id) DO UPDATE SET title=excluded.title,url=excluded.url,
                            description=excluded.description,abstract=excluded.abstract,body=excluded.body,
                            revision_id=excluded.revision_id,wikidata_qid=excluded.wikidata_qid,
                            date_modified=excluded.date_modified,source_file=excluded.source_file,
                            source_row=excluded.source_row
                        WHERE excluded.revision_id > articles.revision_id
                    """, articles)
                connection.execute("INSERT INTO shards VALUES (?,?,?)", (key, fingerprints[key], count))
            print(f"Indexed {file.name}: {count} rows", flush=True)
        snapshot = hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()
        article_count = connection.execute("SELECT count(*) FROM articles").fetchone()[0]
        if not article_count:
            raise ValueError("No English Wikipedia articles found in these Parquet files")
        with connection:
            connection.execute("INSERT OR REPLACE INTO metadata VALUES ('snapshot',?)", (snapshot,))
            connection.execute("INSERT OR REPLACE INTO metadata VALUES ('ready','1')")
        return {"index": str(index_path), "articles": article_count,
                "shards": len(files), "snapshot": snapshot}
    finally:
        connection.close()


class WikipediaIndex:
    def __init__(self, path: Path, allow_partial: bool = False):
        if not path.is_file():
            raise FileNotFoundError(f"Wikipedia index missing: {path}; run src.build_wikipedia_index first")
        self.connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        try:
            metadata = dict(self.connection.execute("SELECT key,value FROM metadata"))
            self.partial = metadata.get("ready") != "1"
            if metadata.get("version") != INDEX_VERSION or (self.partial and not allow_partial):
                raise ValueError("Wikipedia index is incomplete or has an unsupported version")
            shards = list(self.connection.execute("SELECT path,fingerprint FROM shards ORDER BY path"))
            if not shards:
                raise ValueError("Wikipedia index has no completed shards")
            self.coverage = {"partial": self.partial, "indexed_shards": len(shards),
                             "expected_shards": int(metadata["expected_shards"]) if metadata.get("expected_shards") else None}
            self.snapshot = ("partial-" + hashlib.sha256(json.dumps([tuple(r) for r in shards]).encode()).hexdigest()
                             if self.partial else metadata["snapshot"])
            self.metadata = metadata
            self.path = path
        except Exception:
            self.close()
            raise

    def close(self):
        self.connection.close()

    def get(self, doc_id: str, full_text: bool = True) -> dict | None:
        row = self.connection.execute("SELECT * FROM articles WHERE doc_id=?", (doc_id,)).fetchone()
        if row is None:
            return None
        article = dict(row)
        if full_text and self.metadata.get("content_mode") == "remote_metadata":
            from huggingface_hub import HfFileSystem
            cache = self.path.parent / "wikipedia_article_cache" / self.snapshot / f"{doc_id}.json"
            if cache.exists():
                return json.loads(cache.read_text(encoding="utf-8"))
            source = article["source_file"].removeprefix("hf://")
            with HfFileSystem(token=False).open(source, "rb", block_size=65536) as file:
                parquet = pq.ParquetFile(file)
                offset = article["source_row"]
                for group in range(parquet.metadata.num_row_groups):
                    size = parquet.metadata.row_group(group).num_rows
                    if offset < size:
                        columns = [c for c in COLUMNS if c in parquet.schema_arrow.names]
                        raw = parquet.read_row_group(group, columns=columns).slice(offset, 1).to_pylist()[0]
                        full = normalize_article(raw, article["source_file"], article["source_row"])
                        if full is None or full["doc_id"] != doc_id:
                            raise ValueError("Remote article source identity mismatch")
                        cache.parent.mkdir(parents=True, exist_ok=True)
                        cache.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
                        return full
                    offset -= size
            raise ValueError("Remote source row does not exist")
        return article

    def search(self, topics: list[dict], limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 50:
            raise ValueError("Candidate limit must be between 1 and 50")
        scores, matched_queries, matched_topics = {}, {}, {}
        for topic in topics:
            terms = list(dict.fromkeys(topic["search_queries"] + topic["keywords"] + topic["suggested_titles"]))
            weight = 1 / max(1, len(terms))
            for query in terms:
                tokens = re.findall(r"[^\W_]+", query, re.UNICODE)[:12]
                if not tokens:
                    continue
                # Never execute LLM-produced FTS syntax; only quote individual tokens.
                quoted = ['"' + t + '"' for t in tokens]
                expression = " AND ".join(quoted)
                rows = self.connection.execute("""
                    SELECT a.doc_id FROM article_fts JOIN articles a ON a.id=article_fts.rowid
                    WHERE article_fts MATCH ? ORDER BY bm25(article_fts,8.0,3.0,2.0,1.0),a.doc_id LIMIT ?
                """, (expression, max(100, limit * 2))).fetchall()
                if not rows and len(tokens) > 1:
                    rows = self.connection.execute("""
                        SELECT a.doc_id FROM article_fts JOIN articles a ON a.id=article_fts.rowid
                        WHERE article_fts MATCH ? ORDER BY bm25(article_fts,8.0,3.0,2.0,1.0),a.doc_id LIMIT ?
                    """, (" OR ".join(quoted), max(100, limit * 2))).fetchall()
                for rank, row in enumerate(rows, 1):
                    doc_id = row["doc_id"]
                    scores[doc_id] = scores.get(doc_id, 0.0) + weight / (60 + rank)
                    matched_queries.setdefault(doc_id, set()).add(query)
                    matched_topics.setdefault(doc_id, set()).add(topic["label"])
            for title in topic["suggested_titles"]:
                for row in self.connection.execute("SELECT doc_id FROM articles WHERE title=? COLLATE NOCASE", (title,)):
                    doc_id = row["doc_id"]
                    scores[doc_id] = scores.get(doc_id, 0.0) + 0.1
                    matched_queries.setdefault(doc_id, set()).add(title)
                    matched_topics.setdefault(doc_id, set()).add(topic["label"])
        selected = sorted(scores, key=lambda doc: (-scores[doc], doc))[:limit]
        results = []
        for rank, doc_id in enumerate(selected, 1):
            article = self.get(doc_id, full_text=False)
            # Candidate records stay small. Full source text remains retrievable via get().
            article.pop("body")
            article.pop("id")
            results.append(article | {"rank": rank, "lexical_score": scores[doc_id],
                                      "matched_queries": sorted(matched_queries[doc_id]),
                                      "matched_topics": sorted(matched_topics[doc_id])})
        return results
