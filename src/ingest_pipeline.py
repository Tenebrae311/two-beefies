"""Sample -> Nemotron Parse -> passage embeddings -> Britannica LanceDB table.

Run from the repository root: python -m src.ingest_pipeline --count 100
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import lancedb
from lancedb.index import FTS

from src.batch_nemotron_parse import image_to_data_uri, parse_image, parse_settings, sample_rows
from src.query_dataset import DATASET_ID, iter_rows
from two_beefies import config
from two_beefies.embedding import embed_passages
from two_beefies.schema import BritannicaChunk, CHUNK_MATCH_DEFAULTS, ParsedPage
from two_beefies.tables import vector_table
from two_beefies.wiki_prefilter import WikipediaAnalysisBranch, WikipediaPrefilter


def save_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """Bound even very long paragraphs, preferring whitespace boundaries."""
    if size < 1 or overlap < 0 or overlap >= size:
        raise ValueError("Require chunk size > overlap >= 0")
    text = text.strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if boundary > start + max(overlap, size // 2):
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def sample_manifest(run_dir: Path, count: int, seed: int | None, split: str,
                    cache_dir: str) -> dict:
    indexed = (dict(row, dataset_index=i) for i, row in enumerate(
        iter_rows(split=split, cache_dir=cache_dir, streaming=True, decode_images=False)))
    selected = sample_rows(indexed, count, rng=random.Random(seed))
    image_dir = run_dir / "images"
    image_dir.mkdir()
    entries = []
    for position, row in enumerate(selected, 1):
        uri = image_to_data_uri(row["image"])
        image = base64.b64decode(uri.partition(",")[2])
        digest = hashlib.sha256(image).hexdigest()
        # The dataset's id is not a unique page identifier.
        doc_id = f"hf-{split}-{row['dataset_index']}-{digest[:16]}"
        filename = f"{position:03d}_{doc_id}.jpg"
        (image_dir / filename).write_bytes(image)
        entries.append({"doc_id": doc_id, "dataset_id": str(row["id"]),
                        "dataset_index": row["dataset_index"], "position": position,
                        "meta": row.get("meta", ""), "label": int(row["label"]),
                        "image_file": f"images/{filename}", "image_sha256": digest})
    manifest = {"dataset": DATASET_ID, "split": split, "seed": seed, "count": count,
                "entries": entries}
    save_json(run_dir / "manifest.json", manifest)
    return manifest


def chunk_rows(entry: dict, text: str, split: str, model: str, size: int, overlap: int) -> list[dict]:
    meta = str(entry.get("meta", ""))
    edition_match = re.search(r"\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth) edition", meta, re.I)
    editions = dict(zip(("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"),
                        ("1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th")))
    edition = editions[edition_match[1].lower()] if edition_match else None
    return [{"id": f"{entry['doc_id']}-{i}", "doc_id": entry["doc_id"],
             "chunk_index": i, "text": chunk, "title": meta or entry["doc_id"],
             "page_index": entry["dataset_index"], "volume_id": entry["dataset_id"],
             "meta": meta, "illustrated": entry.get("label") == 1,
             "section": None, "url": f"https://huggingface.co/datasets/{DATASET_ID}/viewer/default/{split}?row={entry['dataset_index']}",
             "image_url": None, "edition": edition, "year": None, "volume_label": meta,
             "ocr_model": "parse", "embed_model": model, **CHUNK_MATCH_DEFAULTS}
            for i, chunk in enumerate(chunk_text(text, size, overlap))]


def open_table(uri: str, name: str, model: str):
    return vector_table(lancedb.connect(uri), name, BritannicaChunk, model)


def run_pipeline(*, run_dir: Path, count: int, seed: int | None, split: str, cache_dir: str,
                 resume: bool, parse_url: str, parse_model: str, parse_key: str,
                 embed_url: str, embed_model: str, embed_key: str, db_uri: str,
                 table_name: str, chunk_size: int = 2000, overlap: int = 200,
                 batch_size: int = 16, embedding_enabled: bool = True,
                 wiki_prefilter: WikipediaPrefilter | None = None) -> dict:
    if embedding_enabled and not embed_url:
        raise ValueError("EMBED_URL is required: configure the Nemotron embedding endpoint")
    if not embedding_enabled and wiki_prefilter is None:
        raise ValueError("Enable at least one post-parse branch")
    if count < 1 or batch_size < 1:
        raise ValueError("Count and embedding batch size must be positive")
    chunk_text("validate", chunk_size, overlap)
    table = open_table(db_uri, table_name, embed_model) if embedding_enabled else None
    db = lancedb.connect(db_uri)
    pages = db.create_table(config.BRITANNICA_PAGES_TABLE, schema=ParsedPage, exist_ok=True)
    matches = (db.open_table(config.MATCHES_TABLE)
               if embedding_enabled and config.MATCHES_TABLE in db.list_tables().tables else None)
    manifest_path = run_dir / "manifest.json"
    if resume:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["dataset"] != DATASET_ID:
            raise ValueError("Manifest belongs to another dataset")
    else:
        if run_dir.exists():
            raise ValueError("Run directory already exists; use --resume or a new --run-dir")
        run_dir.mkdir(parents=True)
        manifest = sample_manifest(run_dir, count, seed, split, cache_dir)
    parsed_dir = run_dir / "parsed"
    parsed_dir.mkdir(exist_ok=True)
    summary = {"selected": len(manifest["entries"]), "stored_images": 0,
               "stored_chunks": 0, "failed": 0, "db_uri": db_uri, "table": table_name,
               "parse_model": parse_model, "embed_model": embed_model,
               "chunk_size": chunk_size, "overlap": overlap,
               "wikipedia_processed": 0, "wikipedia_candidates": 0, "parsed_pages": 0}
    log_path = run_dir / "events.jsonl"
    with log_path.open("a", encoding="utf-8") as log:
        for entry in manifest["entries"]:
            doc_id = entry["doc_id"]
            events, failed, text = [], False, None
            try:
                parsed_path = parsed_dir / f"{doc_id}.json"
                cached = json.loads(parsed_path.read_text(encoding="utf-8")) if parsed_path.exists() else None
                if cached and cached["parse_model"] == parse_model and cached["parse_url"] == parse_url:
                    text = cached["text"]
                else:
                    image = (run_dir / entry["image_file"]).read_bytes()
                    if hashlib.sha256(image).hexdigest() != entry["image_sha256"]:
                        raise ValueError("Saved image checksum mismatch")
                    uri = "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii")
                    text, raw = parse_image(uri, parse_key, parse_url, parse_model)
                    save_json(parsed_path, {"doc_id": doc_id, "text": text, "raw_response": raw,
                                           "parse_model": parse_model, "parse_url": parse_url})
                if not text.strip():
                    raise ValueError("Parsed text is empty")
                (parsed_dir / f"{doc_id}.txt").write_text(text + "\n", encoding="utf-8")
                page = {"doc_id": doc_id, "text": text, "meta": entry.get("meta", ""),
                        "dataset_id": entry["dataset_id"], "dataset_index": entry["dataset_index"],
                        "image_file": str((run_dir / entry["image_file"]).resolve()),
                        "parse_model": parse_model, "source_text_sha256": hashlib.sha256(text.encode()).hexdigest()}
                pages.merge_insert("doc_id").when_matched_update_all().when_not_matched_insert_all().execute([page])
                summary["parsed_pages"] += 1
            except Exception as exc:
                text, failed = None, True
                events.append({"doc_id": doc_id, "status": "failed", "stage": "parse",
                               "error": f"{type(exc).__name__}: {exc}"})
            # Both branches consume the same parser checkpoint; one may fail independently.
            if text and wiki_prefilter is not None:
                try:
                    result = wiki_prefilter.match_page(doc_id, text, entry.get("meta", ""), run_dir / "wikipedia")
                    summary["wikipedia_processed"] += 1
                    summary["wikipedia_candidates"] += result["candidate_count"]
                    events.append({"doc_id": doc_id, "stage": "wikipedia", "status": result["status"],
                                   "candidates": result["candidate_count"]})
                    message = "LLM analysis saved" if result["status"] == "analyzed" else f"{result['candidate_count']} Wikipedia candidates"
                    print(f"[{entry['position']}/{summary['selected']}] {message}: {doc_id}", flush=True)
                except Exception as exc:
                    failed = True
                    events.append({"doc_id": doc_id, "status": "failed", "stage": "wikipedia",
                                   "error": f"{type(exc).__name__}: {exc}"})
            if text and embedding_enabled:
                stage = "embed"
                try:
                    rows = chunk_rows(entry, text, manifest["split"], embed_model, chunk_size, overlap)
                    vectors = embed_passages([r["text"] for r in rows], url=embed_url, model=embed_model,
                                             api_key=embed_key, batch_size=batch_size)
                    for row, vector in zip(rows, vectors, strict=True):
                        row["vector"] = vector
                    stage = "store"
                    if matches is not None:
                        matches.delete("britannica_doc_id = '" + doc_id.replace("'", "''") + "'")
                    table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows)
                    table.delete("doc_id = '" + doc_id.replace("'", "''") + f"' AND chunk_index >= {len(rows)}")
                    summary["stored_images"] += 1
                    summary["stored_chunks"] += len(rows)
                    events.append({"doc_id": doc_id, "status": "stored", "stage": "embed",
                                   "chunks": len(rows)})
                    print(f"[{entry['position']}/{summary['selected']}] stored {doc_id}: {len(rows)} chunks", flush=True)
                except Exception as exc:
                    failed = True
                    events.append({"doc_id": doc_id, "status": "failed", "stage": stage,
                                   "error": f"{type(exc).__name__}: {exc}"})
            summary["failed"] += failed
            for event in events:
                log.write(json.dumps(event, ensure_ascii=False) + "\n")
                if event["status"] == "failed":
                    print(f"[{entry['position']}/{summary['selected']}] failed at {event['stage']}", flush=True)
            log.flush()
            save_json(run_dir / "summary.json", summary)
    if summary["stored_chunks"]:
        table.create_index("text", config=FTS(), replace=True)
    save_json(run_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir", default=".hf_cache")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--parse-url")
    parser.add_argument("--parse-model")
    parser.add_argument("--embed-url", default=config.EMBED_URL)
    parser.add_argument("--embed-model", default=config.EMBED_MODEL)
    parser.add_argument("--db-uri", default=config.LANCEDB_URI)
    parser.add_argument("--table", default=config.BRITANNICA_TABLE)
    parser.add_argument("--chunk-size", type=int, default=2000)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--mode", choices=["embeddings", "analysis", "wikipedia", "both"], default="embeddings")
    parser.add_argument("--wiki-index", type=Path, default=Path(config.WIKI_INDEX_PATH))
    parser.add_argument("--candidate-table", default=config.WIKI_CANDIDATES_TABLE)
    parser.add_argument("--analysis-model", default=config.WIKI_ANALYSIS_MODEL)
    parser.add_argument("--top-k", type=int, default=50)
    args = parser.parse_args()
    if args.resume and not args.run_dir:
        parser.error("--resume requires --run-dir")
    if args.mode in {"embeddings", "both"} and not args.embed_url:
        parser.error("Set EMBED_URL in .env or pass --embed-url")
    prefilter = None
    try:
        parse_url, parse_model, parse_key = parse_settings(args.parse_url, args.parse_model)
        if args.mode in {"wikipedia", "both"}:
            prefilter = WikipediaPrefilter(index_path=args.wiki_index, db_uri=args.db_uri,
                                          table_name=args.candidate_table, base_url=config.NEBIUS_BASE_URL,
                                          api_key=config.NEBIUS_API_KEY, model=args.analysis_model, top_k=args.top_k)
        elif args.mode == "analysis":
            prefilter = WikipediaAnalysisBranch(base_url=config.NEBIUS_BASE_URL,
                                               api_key=config.NEBIUS_API_KEY, model=args.analysis_model)
        run_dir = args.run_dir or Path(".data/ingestion") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        summary = run_pipeline(
            run_dir=run_dir, count=args.count, seed=args.seed, split=args.split,
            cache_dir=args.cache_dir, resume=args.resume, parse_url=parse_url,
            parse_model=parse_model, parse_key=parse_key, embed_url=args.embed_url,
            embed_model=args.embed_model, embed_key=config.nim_api_key(args.embed_url), db_uri=args.db_uri,
            table_name=args.table, chunk_size=args.chunk_size, overlap=args.overlap,
            batch_size=args.batch_size, embedding_enabled=args.mode in {"embeddings", "both"},
            wiki_prefilter=prefilter)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    finally:
        if prefilter:
            prefilter.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Run saved to {run_dir}")
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
