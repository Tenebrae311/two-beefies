"""Run the LLM/Wikipedia branch on existing OCR, independently of embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from itertools import groupby, islice
from pathlib import Path

import lancedb

from src.batch_nemotron_parse import extract_text
from two_beefies import config
from two_beefies.wiki_prefilter import WikipediaPrefilter, cached_analysis, save_json


def parsed_documents(*, run_dir: Path | None = None, records: Path | None = None,
                     db_uri: str = "", source_table: str = ""):
    if run_dir is not None:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["entries"]:
            path = run_dir / "parsed" / f"{entry['doc_id']}.json"
            if not path.exists():
                yield {"doc_id": entry["doc_id"], "error": "No successful parser checkpoint"}
                continue
            parsed = json.loads(path.read_text(encoding="utf-8"))
            yield {"doc_id": entry["doc_id"], "text": extract_text(parsed["text"]), "meta": entry.get("meta", "")}
    elif records is not None:
        # Also accept the earlier standalone parser's records.jsonl, including duplicate volume IDs.
        with records.open(encoding="utf-8") as file:
            for position, line in enumerate(file, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                text = extract_text(row.get("text", ""))
                identity = f"{records.resolve()}:{position}:{row.get('id')}:{text}"
                doc_id = "ocr-" + hashlib.sha256(identity.encode()).hexdigest()[:32]
                yield {"doc_id": doc_id, "text": text, "meta": row.get("meta", ""),
                       **({"error": row["error"]} if row.get("error") else {})}
    else:
        table = lancedb.connect(db_uri).open_table(source_table)
        count = table.count_rows()
        if not count:
            return
        rows = table.search().select(["doc_id", "chunk_index", "text", "volume_label"]).limit(count).to_list()
        for doc_id, chunks in groupby(sorted(rows, key=lambda r: (r["doc_id"], r["chunk_index"])), key=lambda r: r["doc_id"]):
            chunks = list(chunks)
            yield {"doc_id": doc_id, "text": "\n\n".join(r["text"] for r in chunks),
                   "meta": chunks[0].get("volume_label") or ""}


def run_matching(documents, prefilter: WikipediaPrefilter | None, output_dir: Path,
                 analysis_settings: dict | None = None) -> dict:
    summary = {"processed": 0, "analyzed": 0, "shortlisted": 0, "candidates": 0, "no_candidates": 0, "failed": 0}
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "events.jsonl").open("a", encoding="utf-8") as log:
        for document in documents:
            summary["processed"] += 1
            try:
                if document.get("error"):
                    raise ValueError(document["error"])
                if prefilter is None:
                    if analysis_settings is None:
                        raise ValueError("No Wikipedia prefilter or analysis settings supplied")
                    cached_analysis(document["doc_id"], document["text"], document["meta"], output_dir,
                                    **analysis_settings)
                    event = {"doc_id": document["doc_id"], "status": "analyzed"}
                    print(f"{document['doc_id']}: analyzed for Wikipedia search", flush=True)
                else:
                    result = prefilter.match_page(document["doc_id"], document["text"], document["meta"], output_dir)
                    summary["shortlisted"] += bool(result["candidate_count"])
                    summary["no_candidates"] += not result["candidate_count"]
                    summary["candidates"] += result["candidate_count"]
                    event = {"doc_id": document["doc_id"], "status": result["status"], "candidates": result["candidate_count"]}
                    print(f"{document['doc_id']}: {result['candidate_count']} Wikipedia candidates", flush=True)
                summary["analyzed"] += 1
            except Exception as exc:
                summary["failed"] += 1
                event = {"doc_id": document["doc_id"], "status": "failed", "error": f"{type(exc).__name__}: {exc}"}
                print(f"{document['doc_id']}: failed ({type(exc).__name__})", flush=True)
            log.write(json.dumps(event, ensure_ascii=False) + "\n")
            log.flush()
            save_json(output_dir / "summary.json", summary)
    save_json(output_dir / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir", type=Path)
    source.add_argument("--records", type=Path)
    source.add_argument("--from-db", action="store_true")
    parser.add_argument("--wiki-index", type=Path, default=Path(config.WIKI_INDEX_PATH))
    parser.add_argument("--db-uri", default=config.LANCEDB_URI)
    parser.add_argument("--source-table", default=config.BRITANNICA_TABLE)
    parser.add_argument("--candidate-table", default=config.WIKI_CANDIDATES_TABLE)
    parser.add_argument("--model", default=config.WIKI_ANALYSIS_MODEL)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--analyze-only", action="store_true", help="Extract search terms without a Wikipedia index")
    parser.add_argument("--limit", type=int, help="Process only the first N existing documents")
    parser.add_argument("--allow-partial-index", action="store_true", help="Explicitly test completed shards of an incomplete index")
    args = parser.parse_args()
    prefilter = None
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    try:
        if not args.analyze_only:
            prefilter = WikipediaPrefilter(index_path=args.wiki_index, db_uri=args.db_uri,
                                          table_name=args.candidate_table, base_url=config.NEBIUS_BASE_URL,
                                          api_key=config.NEBIUS_API_KEY, model=args.model, top_k=args.top_k,
                                          allow_partial_index=args.allow_partial_index)
        output = args.output_dir or ((args.run_dir / "wikipedia") if args.run_dir else
                                    Path(".data/wiki_prefilter") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"))
        documents = parsed_documents(run_dir=args.run_dir, records=args.records,
                                     db_uri=args.db_uri, source_table=args.source_table)
        if args.limit is not None:
            documents = islice(documents, args.limit)
        summary = run_matching(documents, prefilter, output, analysis_settings={
            "base_url": config.NEBIUS_BASE_URL, "api_key": config.NEBIUS_API_KEY, "model": args.model})
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    finally:
        if prefilter:
            prefilter.close()
    print(json.dumps(summary, indent=2))
    print(f"Matching results saved to {output}")
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
