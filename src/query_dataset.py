"""Query the Encyclopaedia Britannica Illustrated dataset.

The dataset is fetched from Hugging Face on demand and cached locally.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from typing import Any

from datasets import load_dataset

DATASET_ID = "NationalLibraryOfScotland/encyclopaedia_britannica_illustrated"
LABEL_NAMES = {0: "not-illustrated", 1: "illustrated"}


def iter_rows(
    split: str = "train",
    cache_dir: str | None = None,
    streaming: bool = True,
) -> Iterator[dict[str, Any]]:
    """Yield dataset rows without requiring a checked-in data copy."""
    dataset = load_dataset(
        DATASET_ID,
        split=split,
        streaming=streaming,
        cache_dir=cache_dir,
    )
    yield from dataset


def query_rows(
    text: str | None = None,
    label: str | None = None,
    record_id: str | None = None,
    limit: int = 20,
    split: str = "train",
    cache_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Find rows by metadata, label, or record id."""
    wanted_label = None
    if label is not None:
        wanted_label = label.lower()
        if wanted_label not in LABEL_NAMES.values():
            raise ValueError(
                f"label must be one of: {', '.join(LABEL_NAMES.values())}"
            )

    needle = text.casefold() if text else None
    results: list[dict[str, Any]] = []
    for row in iter_rows(split=split, cache_dir=cache_dir):
        row_label = LABEL_NAMES.get(int(row["label"]), str(row["label"]))
        if wanted_label and row_label != wanted_label:
            continue
        if record_id and str(row["id"]) != record_id:
            continue
        if needle and needle not in str(row.get("meta", "")).casefold():
            continue

        image = row["image"]
        if hasattr(image, "size"):
            width, height = image.size
        else:
            width = image.get("width")
            height = image.get("height")

        results.append(
            {
                "id": str(row["id"]),
                "label": row_label,
                "meta": row.get("meta", ""),
                "image": {"width": width, "height": height},
            }
        )
        if len(results) >= limit:
            break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", help="case-insensitive search in meta")
    parser.add_argument(
        "--label", choices=sorted(LABEL_NAMES.values()), help="filter by label"
    )
    parser.add_argument("--id", dest="record_id", help="exact record id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir", default=".hf_cache")
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    rows = query_rows(
        text=args.text,
        label=args.label,
        record_id=args.record_id,
        limit=args.limit,
        split=args.split,
        cache_dir=args.cache_dir,
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
