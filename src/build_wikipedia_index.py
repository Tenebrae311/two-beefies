"""Build a reusable SQLite/FTS5 index from downloaded Kaggle enwiki Parquet files."""

import argparse
import json
from pathlib import Path

from two_beefies import config
from two_beefies.wiki_index import build_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Downloaded enwiki directory or Parquet shard")
    parser.add_argument("--index", type=Path, default=Path(config.WIKI_INDEX_PATH))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(build_index(args.source, args.index, args.resume), indent=2))
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
