import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import lancedb
from PIL import Image

from src.ingest_pipeline import chunk_text, open_table, run_pipeline
from two_beefies.embedding import QWEN_EMBED_MODEL, embed_passages
from two_beefies.schema import CHUNK_MATCH_DEFAULTS, EMBED_DIM, Match


class EmbeddingTests(unittest.TestCase):
    def test_nebius_key_is_only_reused_for_official_https_endpoint(self):
        from two_beefies import config
        with patch.object(config, "NIM_API_KEY", ""), patch.object(config, "NEBIUS_API_KEY", "account-key"):
            self.assertEqual(config.nim_api_key("https://api.tokenfactory.nebius.com/v1/embeddings"), "account-key")
            for url in ("https://parser.tunnel.example/v1", "http://api.tokenfactory.nebius.com/v1",
                        "https://api.tokenfactory.nebius.com.evil.example/v1"):
                self.assertEqual(config.nim_api_key(url), "")
        with patch.object(config, "NIM_API_KEY", "explicit-key"):
            self.assertEqual(config.nim_api_key("https://embed.example"), "explicit-key")

    def test_query_and_passage_embedding_urls_agree(self):
        from two_beefies.retrieval import _nim_url
        for base in ("https://embed.example", "https://embed.example/v1/",
                     "https://embed.example/v1/embeddings"):
            self.assertEqual(_nim_url(base, "embeddings"), "https://embed.example/v1/embeddings")

    @patch("two_beefies.embedding.requests.post")
    def test_batches_reorders_and_uses_passage_mode(self, post):
        def respond(_url, **kwargs):
            from unittest.mock import Mock
            response = Mock(status_code=200)
            response.json.return_value = {"data": [
                {"index": i, "embedding": [float(i + 1)] * EMBED_DIM}
                for i in reversed(range(len(kwargs["json"]["input"])))
            ]}
            return response
        post.side_effect = respond
        vectors = embed_passages(["one", "two", "three"], url="https://embed.example/v1/",
                                 model="embed-model", api_key="embed-key", batch_size=2)
        self.assertEqual([v[0] for v in vectors], [1.0, 2.0, 1.0])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args.args[0], "https://embed.example/v1/embeddings")
        self.assertEqual(post.call_args.kwargs["json"]["input_type"], "passage")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer embed-key")

    @patch("two_beefies.embedding.requests.post")
    def test_rejects_missing_indices_wrong_dimensions_and_invalid_vectors(self, post):
        post.return_value.status_code = 200
        for data in ([], [{"index": 0, "embedding": [1.0]}],
                     [{"index": 0, "embedding": [0.0] * EMBED_DIM}],
                     [{"index": 0, "embedding": [float("nan")] * EMBED_DIM}]):
            with self.subTest(data_length=len(data)):
                post.return_value.json.return_value = {"data": data}
                with self.assertRaises(ValueError):
                    embed_passages(["text"], url="https://embed.example", model="embed-model")

    @patch("two_beefies.embedding.requests.post")
    def test_qwen_passages_request_native_dimensions_without_nim_parameters(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"model": QWEN_EMBED_MODEL, "data": [
            {"index": 0, "embedding": [1.0] * EMBED_DIM}]}
        vectors = embed_passages(["Historical astronomy"], url="https://embed.example/v1",
                                 model=QWEN_EMBED_MODEL, api_key="test-key")
        self.assertEqual(len(vectors[0]), EMBED_DIM)
        self.assertEqual(post.call_args.kwargs["json"], {
            "model": QWEN_EMBED_MODEL, "input": ["Historical astronomy"],
            "dimensions": EMBED_DIM, "encoding_format": "float"})

    @patch("two_beefies.embedding.requests.post")
    def test_qwen_queries_use_same_model_dimensions_and_validated_response(self, post):
        from two_beefies import config
        from two_beefies.retrieval import embed_query
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"model": QWEN_EMBED_MODEL, "data": [
            {"index": 0, "embedding": [1.0] * EMBED_DIM}]}
        with patch.object(config, "EMBED_MODEL", QWEN_EMBED_MODEL), patch.object(config, "EMBED_URL", "https://embed.example"):
            self.assertEqual(len(embed_query("What changed in astronomy?")), EMBED_DIM)
            payload = post.call_args.kwargs["json"]
            self.assertEqual(payload["model"], QWEN_EMBED_MODEL)
            self.assertEqual(payload["dimensions"], EMBED_DIM)
            self.assertTrue(payload["input"][0].startswith("Instruct: "))
            self.assertTrue(payload["input"][0].endswith("\nQuery:What changed in astronomy?"))
            post.return_value.json.return_value["data"][0]["embedding"] = [0.0] * EMBED_DIM
            with self.assertRaisesRegex(ValueError, "zero vector"):
                embed_query("Astronomy")

    @patch("two_beefies.embedding.requests.post")
    def test_response_from_another_model_is_rejected(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"model": "another-model", "data": [
            {"index": 0, "embedding": [1.0] * EMBED_DIM}]}
        with self.assertRaisesRegex(ValueError, "model differs"):
            embed_passages(["text"], url="https://embed.example", model=QWEN_EMBED_MODEL)

    @patch("two_beefies.retrieval.embed_query")
    @patch("two_beefies.retrieval._table")
    def test_retrieval_rejects_vectors_from_another_model_before_embedding(self, table, embed):
        from two_beefies import config, retrieval
        table.return_value.count_rows.return_value = 1
        with patch.object(config, "EMBED_URL", "https://embed.example"), patch.object(config, "EMBED_MODEL", QWEN_EMBED_MODEL):
            with self.assertRaisesRegex(ValueError, "model differs"):
                retrieval.search("britannica", "Astronomy")
        embed.assert_not_called()


class ChunkTests(unittest.TestCase):
    def test_bounds_chunks_and_covers_unbroken_input_with_overlap(self):
        text = "".join(str(i % 10) for i in range(431))
        chunks = chunk_text(text, size=100, overlap=20)
        self.assertTrue(all(0 < len(c) <= 100 for c in chunks))
        self.assertEqual(chunks[0] + "".join(c[20:] for c in chunks[1:]), text)

    def test_long_paragraph_and_empty_text(self):
        self.assertTrue(all(len(c) <= 100 for c in chunk_text("word " * 1000, 100, 10)))
        self.assertEqual(chunk_text(" \n "), [])
        with self.assertRaises(ValueError):
            chunk_text("text", 100, 100)


class PipelineTests(unittest.TestCase):
    def settings(self, root):
        return dict(run_dir=root / "run", count=2, seed=42, split="train",
                    cache_dir=str(root / "cache"), resume=False,
                    parse_url="https://parser.example/v1/chat/completions",
                    parse_model="nvidia/nemotron-3.5-parse", parse_key="",
                    embed_url="https://embed.example", embed_model="test-embed",
                    embed_key="", db_uri=str(root / "lancedb"), table_name="britannica_chunks",
                    chunk_size=100, overlap=10)

    @patch("src.ingest_pipeline.embed_passages")
    @patch("src.ingest_pipeline.parse_image")
    @patch("src.ingest_pipeline.iter_rows")
    def test_real_database_resume_failures_and_duplicate_volume_ids(self, rows, parse, embed):
        rows.return_value = [dict(id="same-volume", label=1,
                                  meta="Encyclopaedia Britannica - Third edition, Volume 3",
                                  image=Image.new("RGB", (10, 10), color))
                             for color in ("white", "black")]
        text = "Astronomy planets historical knowledge. " * 10
        parse.return_value = (text, {"choices": [{"message": {"content": text}}]})
        def vectors(texts, **kwargs):
            return [[1.0] * EMBED_DIM for _ in texts]
        # A failed embedding must leave OCR cached for the next run.
        embed.side_effect = [RuntimeError("Temporary embedding outage"), vectors(chunk_text(text, 100, 10))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self.settings(root)
            first = run_pipeline(**settings)
            self.assertEqual(first["failed"], 1)
            self.assertEqual(first["stored_images"], 1)
            self.assertEqual(parse.call_count, 2)
            manifest = json.loads((root / "run/manifest.json").read_text(encoding="utf-8"))
            self.assertNotEqual(manifest["entries"][0]["doc_id"], manifest["entries"][1]["doc_id"])
            settings["resume"] = True
            embed.side_effect = vectors
            second = run_pipeline(**settings)
            self.assertEqual(second["failed"], 0)
            self.assertEqual(second["stored_images"], 2)
            self.assertEqual(parse.call_count, 2)
            self.assertEqual(rows.call_count, 1)
            table = lancedb.connect(settings["db_uri"]).open_table("britannica_chunks")
            count = table.count_rows()
            self.assertEqual(count, second["stored_chunks"])
            hits = table.search([1.0] * EMBED_DIM).distance_type("cosine").limit(1).to_list()
            self.assertEqual(hits[0]["edition"], "3rd")
            self.assertIsInstance(hits[0]["page_index"], int)
            self.assertEqual(hits[0]["volume_id"], "same-volume")
            self.assertTrue(hits[0]["illustrated"])
            self.assertIn("Third edition", hits[0]["meta"])
            self.assertIn("Astronomy", hits[0]["text"])
            self.assertTrue(table.search("Astronomy", query_type="fts").limit(1).to_list())
            # Re-embedding invalidates both direct row links and page summaries.
            table.update(values={"matched_wikipedia_chunk_id": "previous-wp-chunk",
                                 "matched_wikipedia_doc_id": "previous-wp-article",
                                 "match_vector_score": 0.9, "match_no_clear_match": False})
            matches = lancedb.connect(settings["db_uri"]).create_table("matches", schema=Match)
            matches.add([Match(britannica_doc_id=hits[0]["doc_id"], wikipedia_doc_id="previous-wp-article",
                               rank=1, vector_score=0.9).model_dump()])
            third = run_pipeline(**settings)
            table = lancedb.connect(settings["db_uri"]).open_table("britannica_chunks")
            self.assertEqual(table.count_rows(), count)
            self.assertEqual(third["failed"], 0)
            self.assertEqual(lancedb.connect(settings["db_uri"]).open_table("matches").count_rows(), 0)
            self.assertTrue(all(row[name] is None for row in table.to_arrow().to_pylist()
                                for name in CHUNK_MATCH_DEFAULTS))
            # Changed chunking replaces old chunks rather than accumulating them.
            settings["chunk_size"] = 1000
            shorter = run_pipeline(**settings)
            self.assertEqual(shorter["stored_chunks"], 2)
            table = lancedb.connect(settings["db_uri"]).open_table("britannica_chunks")
            self.assertEqual(table.count_rows(), 2)
            with self.assertRaisesRegex(ValueError, "embedding model"):
                open_table(settings["db_uri"], "britannica_chunks", "another-model")

    @patch("src.ingest_pipeline.iter_rows")
    def test_missing_embedder_stops_before_dataset_or_output(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.settings(Path(directory))
            settings["embed_url"] = ""
            with self.assertRaisesRegex(ValueError, "EMBED_URL"):
                run_pipeline(**settings)
            rows.assert_not_called()
            self.assertFalse(settings["run_dir"].exists())

    @patch("src.ingest_pipeline.embed_passages")
    @patch("src.ingest_pipeline.parse_image")
    @patch("src.ingest_pipeline.iter_rows")
    def test_post_parse_branches_fail_independently(self, rows, parse, embed):
        for failing_branch in ("wikipedia", "embed"):
            with self.subTest(failing_branch=failing_branch), tempfile.TemporaryDirectory() as directory:
                rows.return_value = [{"id": "volume", "label": 0, "meta": "Third edition",
                                      "image": Image.new("RGB", (10, 10), "white")}]
                parse.return_value = ("Astronomy planets", {})
                matcher = Mock()
                matcher.match_page.return_value = {"candidate_count": 50, "status": "shortlist"}
                matcher.match_page.side_effect = RuntimeError("LLM unavailable") if failing_branch == "wikipedia" else None
                embed.side_effect = RuntimeError("Embedding unavailable") if failing_branch == "embed" else None
                embed.return_value = [[1.0] * EMBED_DIM]
                settings = self.settings(Path(directory))
                settings["count"] = 1
                settings["wiki_prefilter"] = matcher
                result = run_pipeline(**settings)
                self.assertEqual(result["failed"], 1)
                self.assertEqual(result["stored_images"], int(failing_branch == "wikipedia"))
                self.assertEqual(result["wikipedia_candidates"], 50 if failing_branch == "embed" else 0)


if __name__ == "__main__":
    unittest.main()
