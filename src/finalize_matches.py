"""Embed saved Britannica pages and their Wikipedia shortlist, then persist one top match per page."""

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
from two_beefies.embedding import embed_passages
from two_beefies.schema import BritannicaChunk, Match, WikipediaChunk
from two_beefies.wiki_index import WikipediaIndex
from two_beefies.wiki_prefilter import save_json


def best_passage_cosine(left: list[list[float]], right: list[list[float]]) -> float:
    a, b = np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1] or not a.size or not b.size:
        raise ValueError("Cannot compare empty or incompatible embeddings")
    norms_a, norms_b = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    if not np.isfinite(a).all() or not np.isfinite(b).all() or (norms_a == 0).any() or (norms_b == 0).any():
        raise ValueError("Cannot compare zero or non-finite embeddings")
    return float(np.clip(((a / norms_a[:, None]) @ (b / norms_b[:, None]).T).max(), -1, 1))


def vector_table(db, name, schema, model):
    table = db.create_table(name, schema=schema, exist_ok=True)
    if not table.schema.equals(schema.to_arrow_schema(), check_metadata=False):
        raise ValueError(f"Incompatible schema in {name}")
    quoted = "'" + model.replace("'", "''") + "'"
    if table.count_rows(f"embed_model IS NULL OR embed_model != {quoted}"):
        raise ValueError(f"Embedding model mismatch in {name}")
    return table


def finalize_run(*, run_dir: Path, index_path: Path, db_uri: str, embed_url: str,
                 embed_model: str, embed_key: str, limit: int = 2,
                 candidate_table: str = "wikipedia_candidates", britannica_table: str = "britannica_chunks",
                 wikipedia_table: str = "wikipedia_chunks", matches_table: str = "matches",
                 allow_partial_index: bool = False, max_article_chunks: int = 8,
                 min_score: float = 0.0) -> dict:
    if not embed_url:
        raise ValueError("Nemotron EMBED_URL is missing; final embedding/matching cannot run")
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
            return [json.loads(path.read_text(encoding="utf-8"))["vector"] for path in paths]

        summary = {"processed": 0, "matched": 0, "no_counterpart": 0, "failed": 0,
                   "embed_model": embed_model, "corpus_snapshot": index.snapshot,
                   "corpus_coverage": index.coverage}
        for document in parsed_documents(run_dir=run_dir):
            if summary["processed"] >= limit:
                break
            summary["processed"] += 1
            doc_id = document["doc_id"]
            try:
                if document.get("error"):
                    raise ValueError(document["error"])
                where = "britannica_doc_id = '" + doc_id.replace("'", "''") + "'"
                shortlist = candidates.search().where(where).limit(50).to_list()
                if not shortlist:
                    raise ValueError("No saved Wikipedia shortlist for this document")
                text_hash = hashlib.sha256(document["text"].encode()).hexdigest()
                if any(row["corpus_snapshot"] != index.snapshot or row["source_text_sha256"] != text_hash for row in shortlist):
                    raise ValueError("Stale candidates: OCR text or Wikipedia snapshot changed")
                eb_rows = chunk_rows(entries[doc_id], document["text"], manifest["split"], embed_model, 2000, 200)
                eb_vectors = vectors([r["text"] for r in eb_rows])
                for row, vector in zip(eb_rows, eb_vectors, strict=True):
                    row["vector"] = vector
                eb_predicate = "doc_id = '" + doc_id.replace("'", "''") + "'"
                (eb_table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all()
                 .when_not_matched_by_source_delete(eb_predicate).execute(eb_rows))
                scores = []
                for candidate in sorted(shortlist, key=lambda row: row["rank"]):
                    article = index.get(candidate["wikipedia_doc_id"])
                    if not article or not article["body"].strip():
                        raise ValueError("Candidate source article has no text")
                    chunks = chunk_text(article["body"], 2000, 200)
                    selected = sorted(set(np.linspace(0, len(chunks) - 1,
                                                     min(len(chunks), max_article_chunks), dtype=int).tolist()))
                    wp_vectors = vectors([chunks[i] for i in selected])
                    wp_rows = [WikipediaChunk(
                        id=f"{article['doc_id']}-{i}", doc_id=article["doc_id"], chunk_index=i,
                        title=article["title"], text=chunks[i], url=article["url"],
                        wikidata_qid=article["wikidata_qid"], revision_id=str(article["revision_id"]),
                        date_modified=article.get("date_modified"), embed_model=embed_model,
                        vector=vector).model_dump() for i, vector in zip(selected, wp_vectors, strict=True)]
                    wp_predicate = "doc_id = '" + article["doc_id"].replace("'", "''") + "'"
                    (wp_table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all()
                     .when_not_matched_by_source_delete(wp_predicate).execute(wp_rows))
                    scores.append({"wikipedia_doc_id": article["doc_id"], "title": article["title"],
                                   "score": best_passage_cosine(eb_vectors, wp_vectors),
                                   "lexical_rank": candidate["rank"]})
                scores.sort(key=lambda row: (-row["score"], row["lexical_rank"], row["wikipedia_doc_id"]))
                best = scores[0]
                accepted = best["score"] >= min_score
                match = {"britannica_doc_id": doc_id, "wikipedia_doc_id": best["wikipedia_doc_id"] if accepted else None,
                         "rank": 1, "vector_score": best["score"], "rerank_score": None,
                         "no_clear_match": not accepted,
                         "reason": f"Best passage cosine using {embed_model}; {len(scores)} candidates; "
                                   f"snapshot={index.snapshot}; threshold={min_score}"}
                match_table.merge_insert(["britannica_doc_id", "rank"]).when_matched_update_all().when_not_matched_insert_all().execute([match])
                match_table.delete(where + " AND rank > 1")
                save_json(run_dir / "final_matches" / f"{hashlib.sha256(doc_id.encode()).hexdigest()}.json",
                          {"match": match, "scores": scores, "corpus_coverage": index.coverage,
                           "max_article_chunks": max_article_chunks})
                summary["matched"] += accepted
                summary["no_counterpart"] += not accepted
                print(f"{doc_id} -> {best['title']} cosine={best['score']:.4f}", flush=True)
            except Exception as exc:
                summary["failed"] += 1
                save_json(run_dir / "final_match_errors" / f"{hashlib.sha256(doc_id.encode()).hexdigest()}.json",
                          {"doc_id": doc_id, "error": f"{type(exc).__name__}: {exc}"})
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
    parser.add_argument("--min-score", type=float, default=0.0)
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
