"""Bounded end-to-end runner: two pages by default, saved checkpoints, no automatic bulk import."""

import argparse
import json
from itertools import islice
from pathlib import Path

from src.complete_parsed_run import complete
from src.finalize_matches import finalize_run
from src.ingest_pipeline import sample_manifest
from src.match_wikipedia import parsed_documents, run_matching
from two_beefies import config
from two_beefies.wiki_prefilter import WikipediaPrefilter, save_json


def run(run_dir: Path, count: int = 2, allow_partial_index: bool = False, top_k: int = 50) -> dict:
    if not 1 <= count <= 10:
        raise ValueError("Small-run count must be between 1 and 10")
    matcher = WikipediaPrefilter(index_path=Path(config.WIKI_INDEX_PATH), db_uri=config.LANCEDB_URI,
                                table_name=config.WIKI_CANDIDATES_TABLE, base_url=config.NEBIUS_BASE_URL,
                                api_key=config.NEBIUS_API_KEY, model=config.WIKI_ANALYSIS_MODEL,
                                top_k=top_k, allow_partial_index=allow_partial_index)
    try:
        if not (run_dir / "manifest.json").exists():
            if run_dir.exists():
                raise ValueError("Run directory exists without a manifest; choose another directory")
            run_dir.mkdir(parents=True)
            sample_manifest(run_dir, count, None, "train", ".hf_cache")
        result = {"status": "running", "limit": count}
        result["parsing_and_analysis"] = complete(run_dir, workers=min(2, count), limit=count)
        result["wikipedia"] = run_matching(islice(parsed_documents(run_dir=run_dir), count), matcher, run_dir / "wikipedia")
        if result["parsing_and_analysis"]["failed"] or result["wikipedia"]["failed"]:
            result["status"] = "failed_before_embedding"
        elif not config.EMBED_URL:
            result["status"] = "awaiting_nemotron_embedding_endpoint"
            result["blocker"] = "EMBED_URL is missing; no substitute model or placeholder vectors were used"
        else:
            result["final_matching"] = finalize_run(
                run_dir=run_dir, index_path=Path(config.WIKI_INDEX_PATH), db_uri=config.LANCEDB_URI,
                embed_url=config.EMBED_URL, embed_model=config.EMBED_MODEL,
                embed_key=config.nim_api_key(config.EMBED_URL), limit=count,
                candidate_table=config.WIKI_CANDIDATES_TABLE, britannica_table=config.BRITANNICA_TABLE,
                wikipedia_table=config.WIKIPEDIA_TABLE, matches_table=config.MATCHES_TABLE,
                allow_partial_index=allow_partial_index)
            result["status"] = "completed" if not result["final_matching"]["failed"] else "failed_at_embedding_or_matching"
        save_json(run_dir / "small_pipeline_summary.json", result)
        return result
    finally:
        matcher.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=Path(".data/ingestion/small2"))
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--allow-partial-index", action="store_true")
    args = parser.parse_args()
    try:
        summary = run(args.run_dir, args.count, args.allow_partial_index, args.top_k)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["status"] == "completed" else 2)
