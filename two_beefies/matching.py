"""Exact cosine matching within each Britannica page's Wikipedia shortlist."""

import numpy as np

from two_beefies.schema import EMBED_DIM


def passage_cosines(left: list[list[float]], right: list[list[float]]) -> np.ndarray:
    a, b = np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1] or not a.size or not b.size:
        raise ValueError("Cannot compare empty or incompatible embeddings")

    def normalize(matrix):
        if not np.isfinite(matrix).all():
            raise ValueError("Cannot compare zero or non-finite embeddings")
        scale = np.max(np.abs(matrix), axis=1)
        if (scale == 0).any():
            raise ValueError("Cannot compare zero or non-finite embeddings")
        # Scaling first also avoids overflow/underflow for finite non-unit vectors.
        matrix = matrix / scale[:, None]
        return matrix / np.linalg.norm(matrix, axis=1)[:, None]

    return np.clip(normalize(a) @ normalize(b).T, -1, 1)


def best_passage_cosine(left: list[list[float]], right: list[list[float]]) -> float:
    return float(passage_cosines(left, right).max())


def match_chunks(britannica_rows: list[dict], candidates: list[tuple[dict, list[dict]]],
                 *, min_score: float = -1.0) -> tuple[list[dict], list[dict]]:
    """Return one decision per Britannica row and the legacy page-level ranking.

    An article's score for a Britannica row is the maximum cosine over that
    article's selected chunks. Ties use lexical rank, article ID, chunk index,
    then chunk ID, so storage/input order cannot change the winner.
    """
    if not britannica_rows or not 1 <= len(candidates) <= 50 or not -1 <= min_score <= 1:
        raise ValueError("Require Britannica rows, 1-50 candidates and a valid cosine threshold")
    if len({row["doc_id"] for row in britannica_rows}) != 1:
        raise ValueError("Compare only one Britannica page's shortlist at a time")
    if len({row["id"] for row in britannica_rows}) != len(britannica_rows):
        raise ValueError("Duplicate Britannica chunk IDs")
    model = britannica_rows[0].get("embed_model")

    def vectors(rows):
        if not rows or not model or any(row.get("embed_model") != model for row in rows):
            raise ValueError("Missing chunks or embedding model mismatch")
        if any(len(row["vector"]) != EMBED_DIM for row in rows):
            raise ValueError(f"Expected {EMBED_DIM} embedding dimensions")
        return [row["vector"] for row in rows]

    eb_vectors = vectors(britannica_rows)
    doc_id = britannica_rows[0]["doc_id"]
    best = [None] * len(britannica_rows)
    scores, seen_articles, seen_chunks = [], set(), set()
    for candidate, chunks in sorted(candidates, key=lambda item: (item[0]["rank"], item[0]["wikipedia_doc_id"])):
        article_id = candidate["wikipedia_doc_id"]
        if candidate["britannica_doc_id"] != doc_id or article_id in seen_articles:
            raise ValueError("Foreign or duplicate Wikipedia candidate")
        seen_articles.add(article_id)
        chunks = sorted(chunks, key=lambda row: (row["chunk_index"], row["id"]))
        for chunk in chunks:
            if chunk["doc_id"] != article_id or chunk["id"] in seen_chunks:
                raise ValueError("Foreign or duplicate Wikipedia chunk")
            seen_chunks.add(chunk["id"])
        cosines = passage_cosines(eb_vectors, vectors(chunks))
        scores.append({"wikipedia_doc_id": article_id, "title": candidate["title"],
                       "score": float(cosines.max()), "lexical_rank": candidate["rank"]})
        for i, column in enumerate(cosines.argmax(axis=1)):
            score = float(cosines[i, column])
            if best[i] is None or score > best[i]["vector_score"]:
                best[i] = {"britannica_chunk_id": britannica_rows[i]["id"],
                           "britannica_doc_id": doc_id, "wikipedia_doc_id": article_id,
                           "wikipedia_chunk_id": chunks[column]["id"], "vector_score": score,
                           "rank": 1, "no_clear_match": False}
    for decision in best:
        if decision["vector_score"] < min_score:
            decision.update(wikipedia_doc_id=None, wikipedia_chunk_id=None, no_clear_match=True)
    scores.sort(key=lambda row: (-row["score"], row["lexical_rank"], row["wikipedia_doc_id"]))
    return best, scores
