"""Pick one random dataset image and OCR it into text.

This script downloads the dataset through the Hugging Face ``datasets`` library,
selects a uniformly random row with reservoir sampling, and runs Tesseract OCR
on the selected historical page.
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

try:
    from src.query_dataset import LABEL_NAMES, iter_rows
except ModuleNotFoundError:  # direct invocation: python src/random_image_to_text.py
    from query_dataset import LABEL_NAMES, iter_rows


def choose_random_row(
    rows: Iterable[dict[str, Any]], rng: random.Random | None = None
) -> dict[str, Any]:
    """Choose one row uniformly from an iterable using reservoir sampling."""
    generator = rng or random.Random()
    selected: dict[str, Any] | None = None
    for count, row in enumerate(rows, start=1):
        if generator.randrange(count) == 0:
            selected = row
    if selected is None:
        raise ValueError("The dataset contains no rows")
    return selected


def as_pil_image(value: Any) -> PILImage.Image:
    """Convert a decoded or undecoded Hugging Face image value to PIL."""
    if isinstance(value, PILImage.Image):
        return value
    if isinstance(value, dict):
        if value.get("bytes") is not None:
            return PILImage.open(BytesIO(value["bytes"]))
        if value.get("path"):
            return PILImage.open(value["path"])
    raise TypeError(f"Unsupported image value: {type(value).__name__}")


def image_to_text(image: PILImage.Image, language: str = "eng") -> str:
    """Run Tesseract OCR and return the recognized text."""
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract is missing. Install it with "
            "'python -m pip install pytesseract'. "
            "The Tesseract OCR application must also be installed."
        ) from exc

    try:
        return pytesseract.image_to_string(image, lang=language, config="--psm 6")
    except pytesseract.pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR was not found. Install Tesseract and add it to PATH, "
            "or set pytesseract.pytesseract.tesseract_cmd in this script."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="reproducible random selection")
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir", default=".hf_cache")
    parser.add_argument("--language", default="eng", help="Tesseract language, e.g. eng")
    parser.add_argument("--save-image", type=Path, help="optional output path for the selected image")
    parser.add_argument("--output", type=Path, help="optional text output path")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    row = choose_random_row(
        iter_rows(
            split=args.split,
            cache_dir=args.cache_dir,
            streaming=True,
            decode_images=False,
        ),
        rng=rng,
    )
    image = as_pil_image(row["image"])

    if args.save_image:
        args.save_image.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.save_image)

    text = image_to_text(image, language=args.language).strip()
    result = {
        "id": str(row["id"]),
        "label": LABEL_NAMES.get(int(row["label"]), str(row["label"])),
        "meta": row.get("meta", ""),
        "text": text,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
