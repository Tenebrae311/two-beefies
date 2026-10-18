"""Embed each saved shortlist and link every Britannica chunk to its closest Wikipedia chunk."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import lancedb
import numpy as np
from lancedb.index import FTS

from src.ingest_pipeline import chunk_rows, chunk_text
from src.match_wikipedia import parsed_documents
from two_beefies import config
from two_beefies.embedding import QWEN_EMBED_MODEL, embed_passages
from two_beefies.matching import best_passage_cosine, match_chunks, passage_cosines
from two_beefies.schema import BritannicaChunk, CHUNK_MATCH_DEFAULTS, EMBED_DIM, Match, WikipediaChunk
from two_beefies.tables import vector_table
from two_beefies.wiki_index import WikipediaIndex
from two_beefies.wiki_prefilter import save_json


def quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def stored_rows(table, expected: list[dict]) -> list[dict]:
    """Read back the actual float32 vectors and verify all logical FK targets."""
    ids = [row["id"] for row in expected]
    rows = table.search().where("id IN (" + ", ".join(map(quoted, ids)) + ")").limit(len(ids) + 1).to_list()
    by_id = {row["id"]: row for row in rows}
    if len(rows) != len(ids) or len(by_id) != len(ids) or set(by_id) != set(ids):
        raise ValueError("Missing or duplicate stored embedding rows")
    for row in expected:
        if any(by_id[row["id"]][key] != row[key] for key in ("doc_id", "text", "embed_model")):
            raise ValueError("Stored embedding row changed during matching")
    return [by_id[row_id] for row_id in ids]


def finalize_run(*, run_dir: Path, index_path: Path, db_uri: str, embed_url: str,
                 embed_model: str, embed_key: str, limit: int = 2,
                 candidate_table: str = "wikipedia_candidates", britannica_table: str = "britannica_chunks",
                 wikipedia_table: str = "wikipedia_chunks", matches_table: str = "matches",
                 allow_partial_index: bool = False, max_article_chunks: int = 8,
                 min_score: float = -1.0) -> dict:
    if not embed_url:
        raise ValueError("EMBED_URL is missing; configure Nemotron or the explicit Qwen embedding fallback")
    if limit < 1 or max_article_chunks < 1 or not -1 <= min_score <= 1:
        raise ValueError("Invalid limit, chunk budget or cosine threshold")
    index = WikipediaIndex(index_path, allow_partial=allow_partial_index)
    try:
        db = lancedb.connect(db_uri)
        candidates = db.open_table(candidate_table)
        eb_table = vector_table(db, britannica_table, BritannicaChunk, embed_model)
        wp_table = vector_table(db, wikipedia_table, WikipediaChunk, embed_model)
        match_table = db.create_table(matches_table, schema=Match, exist_ok=True)
        if not match_table.schema.equals(Match.to_arrow_schema(), check_metadata=False):
            raise ValueError("Incompatible final matches schema")
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        entries = {entry["doc_id"]: entry for entry in manifest["entries"]}
        cache_dir = run_dir / "embeddings" / hashlib.sha256(f"{embed_model}\0{embed_url}".encode()).hexdigest()
        cache_dir.mkdir(parents=True, exist_ok=True)

        def vectors(texts):
            paths = [cache_dir / f"{hashlib.sha256(text.encode()).hexdigest()}.json" for text in texts]
            missing = list(dict.fromkeys(text for text, path in zip(texts, paths) if not path.exists()))
            if missing:
                new = embed_passages(missing, url=embed_url, model=embed_model, api_key=embed_key)
                for text, vector in zip(missing, new, strict=True):
                    save_json(cache_dir / f"{hashlib.sha256(text.encode()).hexdigest()}.json", {"vector": vector})
            result = [json.loads(path.read_text(encoding="utf-8"))["vector"] for path in paths]
            if not result or any(len(vector) != EMBED_DIM for vector in result):
                raise ValueError(f"Expected non-empty {EMBED_DIM}-dimensional cached embeddings")
            passage_cosines(result, [result[0]])  # Validate caches as well as fresh API responses.
            return result

        summary = {"processed": 0, "matched": 0, "no_counterpart": 0, "failed": 0,
                   "processed_chunks": 0, "matched_chunks": 0, "no_counterpart_chunks": 0,
                   "embed_model": embed_model, "embed_dim": EMBED_DIM,
                   "embedding_fallback": embed_model == QWEN_EMBED_MODEL, "corpus_snapshot": index.snapshot,
                   "corpus_coverage": index.coverage}
        for document in parsed_documents(run_dir=run_dir):
            if summary["processed"] >= limit:
                break
            summary["processed"] += 1
            doc_id = document["doc_id"]
            where = f"britannica_doc_id = {quoted(doc_id)}"
            eb_predicate = f"doc_id = {quoted(doc_id)}"
            stem = hashlib.sha256(doc_id.encode()).hexdigest()
            final_path = run_dir / "final_matches" / f"{stem}.json"
            error_path = run_dir / "final_match_errors" / f"{stem}.json"

            def clear_matches():
                eb_table.update(where=eb_predicate, values=CHUNK_MATCH_DEFAULTS)
                match_table.delete(where)

            try:
                # A failed/incomplete recomputation must not leave a previous match
                # looking current (especially after an OCR or shortlist change).
                clear_matches()
                if document.get("error"):
                    raise ValueError(document["error"])
                shortlist = candidates.search().where(where).limit(51).to_list()
                if not shortlist:
                    raise ValueError("No saved Wikipedia shortlist for this document")
                if len(shortlist) > 50 or len({row["wikipedia_doc_id"] for row in shortlist}) != len(shortlist):
                    raise ValueError("Require at most 50 distinct Wikipedia candidates per page")
                text_hash = hashlib.sha256(document["text"].encode()).hexdigest()
                if any(row["corpus_snapshot"] != index.snapshot or row["source_text_sha256"] != text_hash for row in shortlist):
                    raise ValueError("Stale candidates: OCR text or Wikipedia snapshot changed")
                eb_rows = chunk_rows(entries[doc_id], document["text"], manifest["split"], embed_model, 2000, 200)
                eb_vectors = vectors([r["text"] for r in eb_rows])
                for row, vector in zip(eb_rows, eb_vectors, strict=True):
                    row["vector"] = vector
                (eb_table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all()
                 .when_not_matched_by_source_delete(eb_predicate).execute(eb_rows))
                eb_rows = stored_rows(eb_table, eb_rows)
                embedded_candidates = []
                print(f"{doc_id}: embedding {len(shortlist)} Wikipedia candidates with {embed_model}", flush=True)
                for number, candidate in enumerate(sorted(shortlist, key=lambda row: (row["rank"], row["wikipedia_doc_id"])), 1):
                    article = index.get(candidate["wikipedia_doc_id"])
                    if not article or not article["body"].strip():
                        raise ValueError("Candidate source article has no text")
                    if (article["doc_id"] != candidate["wikipedia_doc_id"]
                            or str(article["revision_id"]) != candidate["revision_id"]):
                        raise ValueError("Stale candidate: Wikipedia article revision changed")
                    chunks = chunk_text(article["body"], 2000, 200)
                    selected = sorted(set(np.linspace(0, len(chunks) - 1,
                                                     min(len(chunks), max_article_chunks), dtype=int).tolist()))
                    wp_vectors = vectors([chunks[i] for i in selected])
                    wp_rows = [WikipediaChunk(
                        id=f"{article['doc_id']}-{article['revision_id']}-{i}-{hashlib.sha256(chunks[i].encode()).hexdigest()}",
                        doc_id=article["doc_id"], chunk_index=i,
                        title=article["title"], text=chunks[i], url=article["url"],
                        wikidata_qid=article["wikidata_qid"], revision_id=str(article["revision_id"]),
                        date_modified=article.get("date_modified"), embed_model=embed_model,
                        vector=vector).model_dump() for i, vector in zip(selected, wp_vectors, strict=True)]
                    # Content/revision-specific IDs and upsert-only storage keep
                    # other pages' links valid if the article/chunk budget changes.
                    (wp_table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all()
                     .execute(wp_rows))
                    embedded_candidates.append((candidate, stored_rows(wp_table, wp_rows)))
                    if number % 10 == 0 or number == len(shortlist):
                        print(f"{doc_id}: Wikipedia candidates embedded {number}/{len(shortlist)}", flush=True)
                chunk_matches, scores = match_chunks(eb_rows, embedded_candidates, min_score=min_score)
                for row, decision in zip(eb_rows, chunk_matches, strict=True):
                    row.update(matched_wikipedia_chunk_id=decision["wikipedia_chunk_id"],
                               matched_wikipedia_doc_id=decision["wikipedia_doc_id"],
                               match_vector_score=decision["vector_score"],
                               match_no_clear_match=decision["no_clear_match"])
                eb_table.merge_insert("id").when_matched_update_all().execute(eb_rows)
                best = scores[0]
                accepted = best["score"] >= min_score
                match = {"britannica_doc_id": doc_id, "wikipedia_doc_id": best["wikipedia_doc_id"] if accepted else None,
                         "rank": 1, "vector_score": best["score"], "rerank_score": None,
                         "no_clear_match": not accepted,
                         "reason": f"Best passage cosine using {embed_model}; {len(scores)} candidates; "
                                   f"snapshot={index.snapshot}; threshold={min_score}"}
                match_table.merge_insert(["britannica_doc_id", "rank"]).when_matched_update_all().when_not_matched_insert_all().execute([match])
                match_table.delete(where + " AND rank > 1")
                save_json(final_path,
                          {"match": match, "chunk_matches": chunk_matches, "scores": scores, "corpus_coverage": index.coverage,
                           "max_article_chunks": max_article_chunks})
                error_path.unlink(missing_ok=True)
                summary["matched"] += accepted
                summary["no_counterpart"] += not accepted
                summary["processed_chunks"] += len(chunk_matches)
                summary["matched_chunks"] += sum(not row["no_clear_match"] for row in chunk_matches)
                summary["no_counterpart_chunks"] += sum(row["no_clear_match"] for row in chunk_matches)
                print(f"{doc_id}: {len(chunk_matches)} chunk decisions; page -> {best['title']} cosine={best['score']:.4f}", flush=True)
            except Exception as exc:
                clear_matches()
                final_path.unlink(missing_ok=True)
                summary["failed"] += 1
                save_json(error_path, {"doc_id": doc_id, "error": f"{type(exc).__name__}: {exc}"})
                print(f"{doc_id}: final matching failed ({type(exc).__name__})", flush=True)
            save_json(run_dir / "final_match_summary.json", summary)
        if summary["matched"] or summary["no_counterpart"]:
            for table in (eb_table, wp_table):
                table.create_index("text", config=FTS(), replace=True)
        return summary
    finally:
        index.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--wiki-index", type=Path, default=Path(config.WIKI_INDEX_PATH))
    parser.add_argument("--db-uri", default=config.LANCEDB_URI)
    parser.add_argument("--embed-url", default=config.EMBED_URL)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--max-article-chunks", type=int, default=8)
    parser.add_argument("--min-score", type=float, default=-1.0,
                        help="Minimum cosine per Britannica chunk (-1 accepts the nearest candidate)")
    parser.add_argument("--allow-partial-index", action="store_true")
    args = parser.parse_args()
    try:
        summary = finalize_run(run_dir=args.run_dir, index_path=args.wiki_index, db_uri=args.db_uri,
                               embed_url=args.embed_url, embed_model=config.EMBED_MODEL,
                               embed_key=config.nim_api_key(args.embed_url), limit=args.limit,
                               candidate_table=config.WIKI_CANDIDATES_TABLE,
                               britannica_table=config.BRITANNICA_TABLE, wikipedia_table=config.WIKIPEDIA_TABLE,
                               matches_table=config.MATCHES_TABLE, allow_partial_index=args.allow_partial_index,
                               max_article_chunks=args.max_article_chunks, min_score=args.min_score)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(summary, indent=2))
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
