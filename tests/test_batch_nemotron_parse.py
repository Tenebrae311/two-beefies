import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.batch_nemotron_parse import extract_text, main, parse_image, parse_settings, sample_rows


class SampleRowsTests(unittest.TestCase):
    def test_returns_requested_number_without_replacement(self):
        rows = [{"id": str(i)} for i in range(20)]
        selected = sample_rows(rows, 5, rng=random.Random(42))
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({row["id"] for row in selected}), 5)

    def test_rejects_too_small_iterable(self):
        with self.assertRaises(ValueError):
            sample_rows([{"id": "1"}], 2, rng=random.Random(42))


class ParseImageTests(unittest.TestCase):
    @patch.dict(os.environ, {"PARSE_URL": "https://legacy-parser.example/v1/chat/completions",
                             "PARSE_MODEL": "parse-model", "NEBIUS_API_KEY": "account-secret"}, clear=True)
    def test_legacy_parser_url_alias_uses_dedicated_authentication(self):
        url, model, key = parse_settings()
        self.assertEqual(url, "https://legacy-parser.example/v1/chat/completions")
        self.assertEqual(model, "parse-model")
        self.assertEqual(key, "")

    @patch("src.batch_nemotron_parse.parse_image", return_value=("Fixture OCR", {}))
    def test_fixture_ocr_client_uses_shared_parser_without_forwarding_hosted_key(self, parse):
        from two_beefies import config
        from two_beefies.ocr import ocr_parse
        with patch.object(config, "PARSE_URL", "https://parser.example/v1/chat/completions"), \
                patch.object(config, "PARSE_API_KEY", ""), \
                patch.object(config, "NVIDIA_API_KEY", "hosted-only-key"):
            from io import BytesIO
            data = BytesIO()
            Image.new("RGB", (10, 10), "white").save(data, format="JPEG")
            self.assertEqual(ocr_parse(data.getvalue()), "Fixture OCR")
            self.assertEqual(parse.call_args.kwargs["api_key"], "")

    def test_removes_parse_layout_tags_but_preserves_document_content(self):
        text = "<x_0.1><y_0.25>Historical text<class_Text>\n\n<chart>data</chart>"
        self.assertEqual(extract_text(text), "Historical text\n\n<chart>data</chart>")

    @patch.dict(os.environ, {"NEBIUS_API_KEY": "account-secret", "PARSE_MODEL": "parse-model"}, clear=True)
    @patch("src.batch_nemotron_parse.requests.post")
    def test_dedicated_parser_never_receives_token_factory_key(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"choices": [{"message": {"content": "Text"}}]}
        url, model, key = parse_settings("https://parser.example/v1/chat/completions")
        parse_image("image", key, url, model)
        self.assertEqual(key, "")
        self.assertNotIn("Authorization", post.call_args.kwargs["headers"])

    @patch("src.batch_nemotron_parse.requests.post")
    def test_sends_nebius_credentials_and_extracts_plain_text(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": "  Historical text\nSecond line  "}}]
        }
        text, raw = parse_image("data:image/jpeg;base64,abc", "test-key",
                                "https://parse.example/v1/chat/completions", "parse-deployment")
        self.assertEqual(text, "Historical text\nSecond line")
        self.assertIn("choices", raw)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://parse.example/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "parse-deployment")
        self.assertEqual(kwargs["json"]["messages"][0]["content"][1]["image_url"]["url"],
                         "data:image/jpeg;base64,abc")

    @patch("src.batch_nemotron_parse.requests.post")
    def test_extracts_structured_content_blocks(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": [
                {"type": "text", "text": "First paragraph"},
                {"type": "text", "text": "Second paragraph"},
            ]}}]
        }
        text, _ = parse_image("image", "key", "https://parse.example", "parse-model")
        self.assertEqual(text, "First paragraph\n\nSecond paragraph")

    @patch("src.batch_nemotron_parse.requests.post")
    def test_preserves_structured_parse_response_support(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "choices": [{"message": {"tool_calls": [{"function": {
                "arguments": json.dumps({"detections": [{"text": "OCR text"}]})
            }}]}}]
        }
        text, _ = parse_image("image", "key", "https://parse.example", "parse-model")
        self.assertEqual(text, "OCR text")

    @patch("src.batch_nemotron_parse.requests.post")
    def test_empty_response_is_reported_as_failure(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"choices": [{"message": {"content": ""}}]}
        with self.assertRaisesRegex(ValueError, "no extractable text"):
            parse_image("image", "key", "https://parse.example", "parse-model")


class BatchConfigurationTests(unittest.TestCase):
    @patch("src.batch_nemotron_parse.load_dotenv")
    @patch.dict(os.environ, {"NEBIUS_API_KEY": "test-key"}, clear=True)
    @patch("sys.argv", ["batch_nemotron_parse.py"])
    @patch("src.batch_nemotron_parse.iter_rows")
    def test_missing_model_fails_before_loading_dataset(self, rows, _dotenv):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        rows.assert_not_called()

    @patch("src.batch_nemotron_parse.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.argv", ["batch_nemotron_parse.py", "--model", "parse-model"])
    @patch("src.batch_nemotron_parse.iter_rows")
    def test_missing_nebius_key_fails_before_loading_dataset(self, rows, _dotenv):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        rows.assert_not_called()

    @patch("src.batch_nemotron_parse.iter_rows")
    @patch("src.batch_nemotron_parse.requests.post")
    def test_dotenv_configuration_produces_txt_and_jsonl(self, post, rows):
        post.return_value.status_code = 200
        rows.return_value = [
            {"id": "123", "label": 1, "meta": "Britannica",
             "image": Image.new("RGB", (10, 10), color)}
            for color in ("white", "black")
        ]
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Historical OCR text"}}]
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "NEBIUS_API_KEY=dotenv-key\nNEBIUS_BASE_URL=https://nebius.example/v1/\n"
                "PARSE_MODEL=parse-deployment\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), \
                    patch("src.batch_nemotron_parse.__file__", str(root / "src/batch_nemotron_parse.py")), \
                    patch("sys.argv", ["batch_nemotron_parse.py", "--count", "2",
                                       "--output-dir", str(root / "output")]):
                main()
            self.assertEqual((root / "output/text/001_123.txt").read_text(encoding="utf-8"),
                             "Historical OCR text\n")
            self.assertEqual((root / "output/text/002_123.txt").read_text(encoding="utf-8"),
                             "Historical OCR text\n")
            records = (root / "output/records.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 2)
            record = json.loads(records[0])
            self.assertEqual(record["text"], "Historical OCR text")
            self.assertEqual(post.call_args.args[0], "https://nebius.example/v1/chat/completions")
            self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer dotenv-key")
            self.assertEqual(post.call_args.kwargs["json"]["model"], "parse-deployment")


if __name__ == "__main__":
    unittest.main()
