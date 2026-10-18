import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import lancedb
import pyarrow as pa
import pyarrow.parquet as pq

from src.finalize_matches import finalize_run, stored_rows
from src.ingest_pipeline import chunk_rows, open_table
from two_beefies import retrieval
from two_beefies.embedding import QWEN_EMBED_MODEL
from two_beefies.matching import match_chunks, passage_cosines
from two_beefies.schema import BritannicaChunk, CHUNK_MATCH_DEFAULTS, EMBED_DIM, WikipediaCandidate, WikipediaChunk
from two_beefies.wiki_index import WikipediaIndex, build_index


MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2"


def vector(x, y):
    return [float(x), float(y)] + [0.0] * (EMBED_DIM - 2)


def chunk(row_id, doc_id, x, y, index=0):
    return {"id": row_id, "doc_id": doc_id, "chunk_index": index,
            "vector": vector(x, y), "embed_model": MODEL}


def candidate(doc_id, rank, chunks, page="eb"):
    return ({"britannica_doc_id": page, "wikipedia_doc_id": doc_id,
             "rank": rank, "title": f"Article {doc_id}"}, chunks)


class ChunkMatchingTests(unittest.TestCase):
    def test_different_topics_on_same_page_get_different_exact_references(self):
        rows = [chunk("eb-0", "eb", 7, 0), chunk("eb-1", "eb", 0, 9, 1)]
        candidates = [candidate("1", 1, [chunk("1-0", "1", 80, 60), chunk("1-1", "1", 0, 2, 1)]),
                      candidate("2", 2, [chunk("2-0", "2", 3, 0)])]
        matches, scores = match_chunks(rows, candidates)
        self.assertEqual([m["wikipedia_chunk_id"] for m in matches], ["2-0", "1-1"])
        self.assertEqual([m["vector_score"] for m in matches], [1.0, 1.0])
        self.assertEqual(scores[0]["wikipedia_doc_id"], "1")  # Page winner is not every row's winner.

    def test_all_fifty_candidates_are_compared_with_deterministic_ties(self):
        rows = [chunk("eb-0", "eb", 1, 0)]
        candidates = [candidate(str(i), i, [chunk(f"{i}-0", str(i), 1, int(i < 50))])
                      for i in range(1, 51)]
        matches, _ = match_chunks(rows, list(reversed(candidates)))
        self.assertEqual(matches[0]["wikipedia_doc_id"], "50")
        tied = [candidate("z", 2, [chunk("z-0", "z", 1, 0)]),
                candidate("b", 1, [chunk("b-0", "b", 1, 0)]),
                candidate("a", 1, [chunk("a-1", "a", 1, 0, 1), chunk("a-0", "a", 1, 0)])]
        matches, _ = match_chunks(rows, tied)
        self.assertEqual(matches[0]["wikipedia_chunk_id"], "a-0")

    def test_threshold_and_negative_nearest_candidate(self):
        rows = [chunk("eb-0", "eb", 1, 0)]
        candidates = [candidate("1", 1, [chunk("1-0", "1", -1, 1)])]
        matches, _ = match_chunks(rows, candidates)
        self.assertEqual(matches[0]["wikipedia_doc_id"], "1")
        self.assertLess(matches[0]["vector_score"], 0)
        rejected, _ = match_chunks(rows, candidates, min_score=0)
        self.assertTrue(rejected[0]["no_clear_match"])
        self.assertIsNone(rejected[0]["wikipedia_doc_id"])
        self.assertIsNone(rejected[0]["wikipedia_chunk_id"])
        self.assertEqual(rejected[0]["vector_score"], matches[0]["vector_score"])

    def test_invalid_or_incomplete_candidate_sets_are_rejected(self):
        rows = [chunk("eb-0", "eb", 1, 0)]
        good = candidate("1", 1, [chunk("1-0", "1", 1, 0)])
        bad_model = copy.deepcopy(good)
        bad_model[1][0]["embed_model"] = "different-model"
        for candidates in ([], [good] * 51, [good, good], [bad_model], [candidate("1", 1, [])],
                           [candidate("1", 1, good[1], page="other-page")],
                           [candidate("1", 1, [chunk("2-0", "2", 1, 0)])]):
            with self.subTest(candidates=len(candidates)), self.assertRaises(ValueError):
                match_chunks(rows, candidates)

    def test_invalid_vectors_and_extreme_finite_values(self):
        for invalid in ([0.0] * EMBED_DIM, vector(float("nan"), 1), vector(float("inf"), 1), [1.0]):
            with self.subTest(first=invalid[0]), self.assertRaises(ValueError):
                bad = chunk("1-0", "1", 1, 0) | {"vector": invalid}
                match_chunks([chunk("eb-0", "eb", 1, 0)], [candidate("1", 1, [bad])])
        self.assertAlmostEqual(float(passage_cosines([[1e300, 1e300]], [[1e-300, 1e-300]])[0, 0]), 1)


class ChunkLinkIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run_dir = self.root / "run"
        (self.run_dir / "parsed").mkdir(parents=True)
        self.entries = [{"doc_id": name, "dataset_id": "volume", "dataset_index": i,
                         "meta": "Third edition", "label": 0}
                        for i, name in enumerate(("page'one", "page-two"))]
        self.texts = ["A" * 2000 + "B" * 1800, "A" * 80]
        (self.run_dir / "manifest.json").write_text(json.dumps({"split": "train", "entries": self.entries}), encoding="utf-8")
        for entry, text in zip(self.entries, self.texts):
            (self.run_dir / "parsed" / f"{entry['doc_id']}.json").write_text(json.dumps({"text": text}), encoding="utf-8")
        shard = self.root / "enwiki_namespace_0_00000.parquet"
        pq.write_table(pa.Table.from_pylist([
            {"identifier": 1, "name": "First topic", "abstract": "W" * 2000 + "X" * 1800 + "Y" * 1800,
             "url": "https://en.wikipedia.org/wiki/First", "version": {"identifier": 10}},
            {"identifier": 2, "name": "Second topic", "abstract": "Z" * 80,
             "url": "https://en.wikipedia.org/wiki/Second", "version": {"identifier": 20}},
        ]), shard)
        self.index_path = self.root / "wiki.sqlite"
        build_index(shard, self.index_path)
        index = WikipediaIndex(self.index_path)
        self.addCleanup(index.close)
        self.db_uri = str(self.root / "db")
        self.db = lancedb.connect(self.db_uri)
        self.candidates = self.db.create_table("wikipedia_candidates", schema=WikipediaCandidate)
        rows = []
        for entry, text in zip(self.entries, self.texts):
            for article_id, rank in (("2", 1), ("1", 2)):
                article = index.get(article_id)
                rows.append(WikipediaCandidate(
                    id=f"{entry['doc_id']}-{article_id}", britannica_doc_id=entry["doc_id"],
                    wikipedia_doc_id=article_id, rank=rank, lexical_score=1 / rank,
                    title=article["title"], url=article["url"], snippet="", revision_id=str(article["revision_id"]),
                    source_file=article["source_file"], source_row=article["source_row"],
                    corpus_snapshot=index.snapshot, analysis_model="nemotron-analysis",
                    source_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    matched_queries=[], matched_topics=[]).model_dump())
        self.candidates.add(rows)

    @staticmethod
    def fake_embeddings(texts, **kwargs):
        return [vector(7, 0) if (text.count("A") > text.count("B")
                                or text.count("X") > max(text.count("W"), text.count("Y")))
                else vector(0, 9) for text in texts]

    def finalize(self, **kwargs):
        return finalize_run(run_dir=self.run_dir, index_path=self.index_path, db_uri=self.db_uri,
                            embed_url="https://embed.test", embed_model=MODEL, embed_key="", **kwargs)

    def rows(self):
        return sorted(self.db.open_table("britannica_chunks").to_arrow().to_pylist(),
                      key=lambda row: (row["doc_id"], row["chunk_index"]))

    def counterparts(self, row):
        with patch.object(retrieval, "_db", return_value=self.db), patch.object(
                retrieval, "_table", side_effect=lambda source: self.db.open_table(f"{source}_chunks")):
            return retrieval.counterparts("EB:" + row["id"])

    def test_persists_exact_links_reuses_cache_and_reads_chunk_level_counterparts(self):
        with patch("src.finalize_matches.embed_passages", side_effect=self.fake_embeddings):
            result = self.finalize(limit=1)
        self.assertEqual((result["failed"], result["matched_chunks"], result["processed_chunks"]), (0, 2, 2))
        rows = self.rows()
        self.assertEqual([r["matched_wikipedia_doc_id"] for r in rows], ["1", "2"])
        wp = self.db.open_table("wikipedia_chunks")
        count = wp.count_rows()
        for row in rows:
            target = wp.search().where(f"id = '{row['matched_wikipedia_chunk_id']}'").limit(1).to_list()[0]
            self.assertEqual(target["doc_id"], row["matched_wikipedia_doc_id"])
            self.assertAlmostEqual(row["match_vector_score"], 1)
            found = self.counterparts(row)
            self.assertEqual(found[0]["wikipedia_cite_id"], "WP:" + target["id"])
            self.assertEqual(found[0]["wikipedia_chunk_id"], target["id"])
        # Page-level summary chooses article 2, while the first row points to article 1.
        self.assertEqual(self.db.open_table("matches").to_arrow().to_pylist()[0]["wikipedia_doc_id"], "2")
        with patch("src.finalize_matches.embed_passages", side_effect=AssertionError("cache must be reused")) as embed:
            again = self.finalize(limit=1)
        embed.assert_not_called()
        self.assertEqual(again["failed"], 0)
        self.assertEqual(self.rows(), rows)
        self.assertEqual(self.db.open_table("wikipedia_chunks").count_rows(), count)
        report = json.loads(next((self.run_dir / "final_matches").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(len(report["chunk_matches"]), 2)

    def test_smaller_article_chunk_budget_preserves_other_pages_foreign_keys(self):
        with patch("src.finalize_matches.embed_passages", side_effect=self.fake_embeddings):
            self.assertEqual(self.finalize(limit=2, max_article_chunks=3)["failed"], 0)
            other = next(row for row in self.rows() if row["doc_id"] == "page-two")
            self.assertEqual(self.finalize(limit=1, max_article_chunks=1)["failed"], 0)
        self.assertEqual(next(row for row in self.rows() if row["doc_id"] == "page-two"), other)
        self.assertEqual(self.counterparts(other)[0]["wikipedia_cite_id"], "WP:" + other["matched_wikipedia_chunk_id"])

    def test_threshold_recomputation_clears_old_link_and_does_not_fall_back_to_page_match(self):
        def embed(texts, **kwargs):
            return [vector(2, 1) if text.startswith("A") and text.count("A") > text.count("B")
                    else self.fake_embeddings([text])[0] for text in texts]
        with patch("src.finalize_matches.embed_passages", side_effect=embed):
            self.assertEqual(self.finalize(limit=1)["matched_chunks"], 2)
            result = self.finalize(limit=1, min_score=0.95)
        self.assertEqual((result["matched_chunks"], result["no_counterpart_chunks"]), (1, 1))
        first = self.rows()[0]
        self.assertTrue(first["match_no_clear_match"])
        self.assertIsNone(first["matched_wikipedia_doc_id"])
        self.assertIsNone(first["matched_wikipedia_chunk_id"])
        self.assertAlmostEqual(first["match_vector_score"], 2 / (5 ** 0.5))
        found = self.counterparts(first)
        self.assertTrue(found[0]["no_clear_match"])
        self.assertNotIn("wikipedia_cite_id", found[0])

    def test_stale_or_incomplete_shortlist_invalidates_only_affected_page(self):
        with patch("src.finalize_matches.embed_passages", side_effect=self.fake_embeddings):
            self.assertEqual(self.finalize(limit=2)["failed"], 0)
            other = next(row for row in self.rows() if row["doc_id"] == "page-two")
            self.candidates.update(where="britannica_doc_id = 'page''one'", values={"source_text_sha256": "stale"})
            result = self.finalize(limit=1)
        self.assertEqual(result["failed"], 1)
        for row in self.rows():
            if row["doc_id"] == "page-two":
                self.assertEqual(row, other)
            else:
                for name in CHUNK_MATCH_DEFAULTS:
                    self.assertIsNone(row[name])
                self.assertEqual(self.counterparts(row), [])
        matches = self.db.open_table("matches").to_arrow().to_pylist()
        self.assertEqual([row["britannica_doc_id"] for row in matches], ["page-two"])
        self.assertEqual(len(list((self.run_dir / "final_matches").glob("*.json"))), 1)

    def test_missing_article_prevents_partial_winner_and_records_failure(self):
        original_get = WikipediaIndex.get
        with patch("src.finalize_matches.embed_passages", side_effect=self.fake_embeddings), patch(
                "src.finalize_matches.WikipediaIndex.get", autospec=True,
                side_effect=lambda index, doc_id: None if doc_id == "1" else original_get(index, doc_id)):
            result = self.finalize(limit=1)
        self.assertEqual(result["failed"], 1)
        self.assertTrue(all(row["matched_wikipedia_chunk_id"] is None for row in self.rows()))
        self.assertEqual(self.db.open_table("matches").count_rows(), 0)
        self.assertEqual(self.db.open_table("wikipedia_chunks").count_rows(), 1)

    def test_corrupt_embedding_cache_is_rejected_before_vectors_are_written(self):
        namespace = hashlib.sha256(f"{MODEL}\0https://embed.test".encode()).hexdigest()
        cache = self.run_dir / "embeddings" / namespace
        cache.mkdir(parents=True)
        for row in chunk_rows(self.entries[0], self.texts[0], "train", MODEL, 2000, 200):
            (cache / f"{hashlib.sha256(row['text'].encode()).hexdigest()}.json").write_text(
                json.dumps({"vector": [0.0] * EMBED_DIM}), encoding="utf-8")
        with patch("src.finalize_matches.embed_passages") as embed:
            result = self.finalize(limit=1)
        embed.assert_not_called()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(self.db.open_table("britannica_chunks").count_rows(), 0)

    def test_schema_migration_preserves_old_vectors_and_rejects_other_models(self):
        row = chunk_rows(self.entries[0], "Saved OCR", "train", MODEL, 2000, 200)[0] | {"vector": vector(3, 4)}
        legacy = {name: value for name, value in row.items() if name not in CHUNK_MATCH_DEFAULTS}
        schema = pa.schema([field for field in BritannicaChunk.to_arrow_schema() if field.name not in CHUNK_MATCH_DEFAULTS])
        table = self.db.create_table("britannica_chunks", schema=schema)
        table.add([legacy])
        with self.assertRaisesRegex(ValueError, "embedding model"):
            open_table(self.db_uri, "britannica_chunks", "other-model")
        self.assertEqual(table.schema.names, schema.names)
        table = open_table(self.db_uri, "britannica_chunks", MODEL)
        migrated = table.to_arrow().to_pylist()[0]
        self.assertEqual(migrated, row)
        self.assertEqual(open_table(self.db_uri, "britannica_chunks", MODEL).count_rows(), 1)
        table.add_columns(pa.schema([pa.field("unexpected", pa.string())]))
        with self.assertRaisesRegex(ValueError, "Incompatible schema"):
            open_table(self.db_uri, "britannica_chunks", MODEL)

    def test_missing_or_duplicate_fk_targets_are_rejected(self):
        table = self.db.create_table("wikipedia_chunks", schema=WikipediaChunk)
        row = WikipediaChunk(id="1-0", doc_id="1", chunk_index=0, title="Article", text="Text",
                             vector=vector(1, 0), embed_model=MODEL).model_dump()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            stored_rows(table, [row])
        table.add([row, row])
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            stored_rows(table, [row])

    def test_qwen_adapter_runs_through_to_real_database_matches(self):
        def respond(url, **kwargs):
            payload = kwargs["json"]
            self.assertEqual(payload["model"], QWEN_EMBED_MODEL)
            self.assertEqual(payload["dimensions"], EMBED_DIM)
            self.assertNotIn("input_type", payload)
            response = Mock(status_code=200)
            response.json.return_value = {"model": QWEN_EMBED_MODEL, "data": [
                {"index": i, "embedding": v} for i, v in enumerate(self.fake_embeddings(payload["input"]))]}
            return response

        with patch("two_beefies.embedding.requests.post", side_effect=respond):
            result = finalize_run(run_dir=self.run_dir, index_path=self.index_path, db_uri=self.db_uri,
                                  embed_url="https://embed.test", embed_model=QWEN_EMBED_MODEL, embed_key="", limit=1)
        self.assertEqual(result["failed"], 0)
        self.assertTrue(result["embedding_fallback"])
        self.assertEqual(result["embed_model"], QWEN_EMBED_MODEL)
        self.assertEqual(result["matched_chunks"], 2)
        self.assertTrue(all(row["embed_model"] == QWEN_EMBED_MODEL for row in self.rows()))


if __name__ == "__main__":
    unittest.main()
