"""Finish a saved sampling run concurrently; persist successful OCR independently of LLM failures."""

import argparse
import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import lancedb

from src.batch_nemotron_parse import parse_image, parse_settings
from two_beefies import config
from two_beefies.schema import ParsedPage
from two_beefies.wiki_prefilter import cached_analysis, save_json


def complete(run_dir: Path, workers: int = 4, limit: int | None = None) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["entries"][:limit] if limit is not None else manifest["entries"]
    summary_file = "completion_summary.json" if limit is None else f"completion_first_{limit}_summary.json"
    url, model, key = parse_settings()
    parsed_dir = run_dir / "parsed"
    parsed_dir.mkdir(exist_ok=True)
    table = lancedb.connect(config.LANCEDB_URI).create_table(config.BRITANNICA_PAGES_TABLE, schema=ParsedPage, exist_ok=True)

    def worker(entry):
        doc_id = entry["doc_id"]
        path = parsed_dir / f"{doc_id}.json"
        try:
            old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            if old and old["parse_model"] == model and old["parse_url"] == url:
                text = old["text"]
            else:
                image = (run_dir / entry["image_file"]).read_bytes()
                if hashlib.sha256(image).hexdigest() != entry["image_sha256"]:
                    raise ValueError("Image checksum mismatch")
                text, raw = parse_image("data:image/jpeg;base64," + base64.b64encode(image).decode(), key, url, model)
                save_json(path, {"doc_id": doc_id, "text": text, "raw_response": raw,
                                 "parse_model": model, "parse_url": url})
            (parsed_dir / f"{doc_id}.txt").write_text(text + "\n", encoding="utf-8")
            page = {"doc_id": doc_id, "text": text, "meta": entry.get("meta", ""),
                    "dataset_id": entry["dataset_id"], "dataset_index": entry["dataset_index"],
                    "image_file": str((run_dir / entry["image_file"]).resolve()), "parse_model": model,
                    "source_text_sha256": hashlib.sha256(text.encode()).hexdigest()}
        except Exception as exc:
            return entry, None, f"parse: {type(exc).__name__}: {exc}"
        try:
            cached_analysis(doc_id, text, entry.get("meta", ""), run_dir / "wikipedia",
                            base_url=config.NEBIUS_BASE_URL, api_key=config.NEBIUS_API_KEY,
                            model=config.WIKI_ANALYSIS_MODEL)
            return entry, page, None
        except Exception as exc:
            return entry, page, f"analysis: {type(exc).__name__}: {exc}"

    summary = {"selected": len(entries), "parsed_pages": 0, "analyzed_pages": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool, (run_dir / "completion_events.jsonl").open("a", encoding="utf-8") as log:
        futures = [pool.submit(worker, entry) for entry in entries]
        for future in as_completed(futures):
            entry, page, error = future.result()
            if page:
                table.merge_insert("doc_id").when_matched_update_all().when_not_matched_insert_all().execute([page])
                summary["parsed_pages"] += 1
            if error:
                summary["failed"] += 1
            else:
                summary["analyzed_pages"] += 1
            event = {"doc_id": entry["doc_id"], "position": entry["position"], "error": error}
            log.write(json.dumps(event, ensure_ascii=False) + "\n")
            log.flush()
            save_json(run_dir / summary_file, summary)
            print(f"Completed {summary['analyzed_pages'] + summary['failed']}/{summary['selected']}: {entry['doc_id']} {'OK' if not error else 'FAILED'}", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    result = complete(args.run_dir, args.workers)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["failed"] else 0)
