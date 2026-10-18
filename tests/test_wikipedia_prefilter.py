import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lancedb
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

from src.ingest_pipeline import run_pipeline
from src.match_wikipedia import parsed_documents, run_matching
from two_beefies.wiki_index import WikipediaIndex, build_index
from two_beefies.wiki_prefilter import WikipediaPrefilter, analyze_page, analysis_input


ANALYSIS = {"summary": "A historical page about astronomy and planets.", "topics": [
    {"label": "Astronomy", "keywords": ["astronomy", "planets"],
     "search_queries": ["planetary motion"], "suggested_titles": ["Solar System", "Imaginary article title"]}
]}


def article(identifier, title, *, version=1, body="Astronomy planets and planetary motion."):
    return {"identifier": identifier, "name": title,
            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
            "abstract": body, "description": "Encyclopaedia article",
            "sections": json.dumps([{"type": "section", "name": "History", "has_parts": [
                {"type": "paragraph", "value": body,
                 "links": [{"url": "https://ignored.example", "text": "not indexed link metadata"}]}]}]),
            "version": {"identifier": version}, "main_entity": {"identifier": f"Q{identifier}"}}


class IndexAndMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.shard = self.root / "enwiki_namespace_0_00000.parquet"
        rows = [article(1, "Solar System", version=2)]
        rows += [article(i, f"Planetary astronomy {i}") for i in range(2, 65)]
        rows += [article(1, "Outdated article title", version=1, body="Old discarded words")]
        rows += [article(100, "Botany", body="Botany flowers calyx stamens")]
        french = article(200, "Astronomie")
        french["url"] = "https://fr.wikipedia.org/wiki/Astronomie"
        rows.append(french)
        pq.write_table(pa.Table.from_pylist(rows), self.shard)
        self.index_path = self.root / "wiki.sqlite"
        self.result = build_index(self.shard, self.index_path)

    def matcher(self):
        matcher = WikipediaPrefilter(index_path=self.index_path, db_uri=str(self.root / "db"),
                                     table_name="wikipedia_candidates", base_url="https://nebius.example/v1",
                                     api_key="test-key", model="nvidia/Nemotron-3.5-Super-VL")
        self.addCleanup(matcher.close)
        return matcher

    def test_real_parquet_index_top50_dedup_and_full_source_lookup(self):
        index = WikipediaIndex(self.index_path)
        self.addCleanup(index.close)
        self.assertEqual(self.result["articles"], 65)
        candidates = index.search(ANALYSIS["topics"])
        self.assertEqual(len(candidates), 50)
        self.assertEqual(len({c["doc_id"] for c in candidates}), 50)
        self.assertEqual(candidates[0]["title"], "Solar System")
        self.assertEqual(index.get("1")["revision_id"], 2)
        self.assertIsNone(index.get("200"))
        source = index.get(candidates[0]["doc_id"])
        self.assertIn("planetary motion", source["body"])
        self.assertNotIn("not indexed link metadata", source["body"])
        self.assertEqual(source["source_row"], 0)
        self.assertEqual(index.search([dict(ANALYSIS["topics"][0], keywords=["zzzznotfound"],
                                          search_queries=["zzzznotfound"], suggested_titles=[])]), [])
        botany = index.search([{"label": "Botany", "keywords": ["flowers"],
                                "search_queries": ["botany calyx"], "suggested_titles": ["Botany"]}])
        self.assertEqual([a["doc_id"] for a in botany], ["100"])

    def test_resume_and_reject_changed_dump(self):
        result = build_index(self.shard, self.index_path, resume=True)
        self.assertEqual(result, self.result)
        pq.write_table(pa.Table.from_pylist([article(999, "New file")]), self.shard)
        with self.assertRaisesRegex(ValueError, "changed"):
            build_index(self.shard, self.index_path, resume=True)

    def test_newer_revision_updates_fulltext_index(self):
        newer = self.root / "enwiki_namespace_0_00001.parquet"
        pq.write_table(pa.Table.from_pylist([article(1, "Updated Solar System", version=3,
                                                   body="uniquerevisiontoken astronomy")]), newer)
        build_index(self.root, self.index_path, resume=True)
        index = WikipediaIndex(self.index_path)
        self.addCleanup(index.close)
        candidates = index.search([{"label": "Revision", "keywords": ["uniquerevisiontoken"],
                                    "search_queries": ["uniquerevisiontoken"], "suggested_titles": []}])
        self.assertEqual(candidates[0]["doc_id"], "1")
        self.assertEqual(candidates[0]["revision_id"], 3)

    def test_query_punctuation_is_not_executed_as_fts_syntax(self):
        index = WikipediaIndex(self.index_path)
        self.addCleanup(index.close)
        topics = [{"label": "Punctuation", "keywords": ['" OR * NEAR( )'],
                   "search_queries": ["*"], "suggested_titles": []}]
        self.assertEqual(index.search(topics), [])

    @patch("two_beefies.wiki_prefilter.requests.post")
    def test_llm_cache_real_lancedb_and_replacement_scoped_to_document(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(ANALYSIS)}}]}
        matcher = self.matcher()
        output = self.root / "output"
        first = matcher.match_page("page'one", "The old astronomy page", "Third edition", output)
        self.assertEqual(first["candidate_count"], 50)
        self.assertEqual(post.call_args.kwargs["json"]["model"], "nvidia/Nemotron-3.5-Super-VL")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        matcher.match_page("page'one", "The old astronomy page", "Third edition", output)
        self.assertEqual(post.call_count, 1)
        matcher.match_page("page-two", "A second page about planets", "Third edition", output)
        matcher.top_k = 1
        matcher.match_page("page'one", "The old astronomy page", "Third edition", output)
        self.assertEqual(matcher.table.count_rows(), 51)
        self.assertEqual(post.call_count, 2)
        matcher.match_page("page'one", "Changed OCR text", "Third edition", output)
        self.assertEqual(post.call_count, 3)
        post.return_value.json.return_value = {"choices": [{"message": {
            "content": json.dumps({"summary": "Unreadable OCR", "topics": []})}}]}
        none = matcher.match_page("page'one", "Unreadable updated OCR", "", output)
        self.assertEqual(none["candidate_count"], 0)
        self.assertEqual(matcher.table.count_rows(), 50)
        self.assertEqual(len(list((output / "analysis").glob("*.json"))), 2)
        self.assertEqual(len(list((output / "candidates").glob("*.json"))), 2)

    @patch("src.ingest_pipeline.open_table")
    @patch("src.ingest_pipeline.iter_rows")
    @patch("src.ingest_pipeline.parse_image")
    @patch("two_beefies.wiki_prefilter.requests.post")
    def test_branch_runs_after_parsing_without_embedding_endpoint(self, post, parse, rows, open_embed_table):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"choices": [{"message": {"content": json.dumps(ANALYSIS)}}]}
        parse.return_value = ("Historical astronomy text", {"test": "raw parser output"})
        rows.return_value = [{"id": "volume", "label": 0, "meta": "Third edition",
                              "image": Image.new("RGB", (10, 10), "white")}]
        matcher = self.matcher()
        result = run_pipeline(run_dir=self.root / "run", count=1, seed=42, split="train",
                              cache_dir=str(self.root / "cache"), resume=False,
                              parse_url="https://parser.example/v1/chat/completions", parse_model="parse",
                              parse_key="", embed_url="", embed_model="", embed_key="",
                              db_uri=str(self.root / "db"), table_name="britannica_chunks",
                              embedding_enabled=False, wiki_prefilter=matcher)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["wikipedia_candidates"], 50)
        self.assertEqual(result["stored_chunks"], 0)
        open_embed_table.assert_not_called()
        docs = list(parsed_documents(run_dir=self.root / "run"))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["text"], "Historical astronomy text")
        again = run_matching(docs, matcher, self.root / "run/wikipedia")
        self.assertEqual(again["candidates"], 50)
        self.assertEqual(post.call_count, 1)
        from src.finalize_matches import finalize_run
        from two_beefies.schema import EMBED_DIM
        with patch("src.finalize_matches.embed_passages", side_effect=lambda texts, **kwargs: [[1.0] * EMBED_DIM for _ in texts]):
            final = finalize_run(run_dir=self.root / "run", index_path=self.index_path,
                                 db_uri=str(self.root / "db"), embed_url="https://embed.example",
                                 embed_model="test-nemotron", embed_key="", limit=1)
            self.assertEqual(final["matched"], 1)
            self.assertEqual(final["failed"], 0)
            database = lancedb.connect(str(self.root / "db"))
            match = database.open_table("matches").to_arrow().to_pylist()[0]
            self.assertEqual(match["wikipedia_doc_id"], "1")
            self.assertEqual(database.open_table("wikipedia_chunks").count_rows(), 50)
            self.assertEqual(database.open_table("britannica_chunks").count_rows(), 1)


class AnalysisTests(unittest.TestCase):
    def test_final_cosine_and_missing_embedder_guard(self):
        from src.finalize_matches import best_passage_cosine, finalize_run
        self.assertAlmostEqual(best_passage_cosine([[1, 0]], [[0, 1], [1, 0]]), 1)
        self.assertAlmostEqual(best_passage_cosine([[1, 0]], [[0, 1]]), 0)
        with self.assertRaises(ValueError):
            best_passage_cosine([[0, 0]], [[1, 0]])
        with self.assertRaisesRegex(ValueError, "EMBED_URL"):
            finalize_run(run_dir=Path("missing"), index_path=Path("missing"), db_uri="missing",
                         embed_url="", embed_model="nemotron", embed_key="")

    @patch("two_beefies.wiki_prefilter.requests.post")
    def test_keyword_overflow_is_bounded_before_validation(self, post):
        post.return_value.status_code = 200
        analysis = json.loads(json.dumps(ANALYSIS))
        analysis["topics"][0]["keywords"] = [f"term{i}" for i in range(20)]
        post.return_value.json.return_value = {"choices": [{"message": {"content": json.dumps(analysis)}}]}
        result, _ = analyze_page("OCR", "Meta", base_url="https://nebius.example/v1", api_key="key", model="nemotron")
        self.assertEqual(len(result["topics"][0]["keywords"]), 12)
    @patch("two_beefies.wiki_prefilter.requests.post")
    def test_analysis_only_needs_no_corpus_and_can_reuse_checkpoint(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"choices": [{"message": {"content": json.dumps(ANALYSIS)}}]}
        documents = [{"doc_id": "page-one", "text": "Astronomy", "meta": "Third edition"}]
        settings = {"base_url": "https://nebius.example/v1", "api_key": "key", "model": "nemotron"}
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                summary = run_matching(documents, None, Path(directory), settings)
                self.assertEqual(summary["analyzed"], 1)
                self.assertEqual(summary["candidates"], 0)
                self.assertEqual(summary["no_candidates"], 0)
            self.assertEqual(post.call_count, 1)

    def test_long_pages_cover_all_regions(self):
        text = "A" * 30000 + "B" * 30000 + "C" * 30000
        excerpts = analysis_input(text)
        self.assertIn("A" * 100, excerpts)
        self.assertIn("B" * 100, excerpts)
        self.assertIn("C" * 100, excerpts)

    @patch("two_beefies.wiki_prefilter.requests.post")
    def test_invalid_and_truncated_llm_responses_are_not_accepted(self, post):
        post.return_value.status_code = 200
        for content, reason in (("not JSON", "stop"), (json.dumps(ANALYSIS), "length")):
            post.return_value.json.return_value = {"choices": [{"finish_reason": reason,
                                                                "message": {"content": content}}]}
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                analyze_page("OCR", "Meta", base_url="https://nebius.example/v1", api_key="key", model="model")

    def test_legacy_parser_records_keep_repeated_ids_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            records = Path(directory) / "records.jsonl"
            records.write_text("\n".join(json.dumps(row) for row in [
                {"id": "volume", "text": "Astronomy"}, {"id": "volume", "text": "Botany"},
                {"id": "failed", "error": "Parse failed"}]), encoding="utf-8")
            docs = list(parsed_documents(records=records))
            self.assertEqual(len(docs), 3)
            self.assertNotEqual(docs[0]["doc_id"], docs[1]["doc_id"])
            self.assertEqual(docs[2]["error"], "Parse failed")


if __name__ == "__main__":
    unittest.main()
