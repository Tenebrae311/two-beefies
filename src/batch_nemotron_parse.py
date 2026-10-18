"""Sample random dataset images and parse them with Nemotron Parse via Nebius."""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import time
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import Image as PILImage

try:
    from src.query_dataset import LABEL_NAMES, iter_rows
except ModuleNotFoundError:  # direct invocation: python src/batch_nemotron_parse.py
    from query_dataset import LABEL_NAMES, iter_rows

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
MAX_INLINE_BYTES = 180_000
LAYOUT_TAG_RE = re.compile(r"<(?:[xy]_[0-9.]+|class_[^<>]+)>")


def sample_rows(
    rows: Iterable[dict[str, Any]],
    count: int,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """Select count rows uniformly without replacement via reservoir sampling."""
    if count < 1:
        raise ValueError("count must be at least 1")

    generator = rng or random.Random()
    reservoir: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if index < count:
            reservoir.append(row)
            continue
        replacement = generator.randrange(index + 1)
        if replacement < count:
            reservoir[replacement] = row

    if len(reservoir) < count:
        raise ValueError(f"Dataset contains only {len(reservoir)} rows; need {count}")
    generator.shuffle(reservoir)
    return reservoir


def image_to_data_uri(value: Any) -> str:
    """Convert a dataset image to a JPEG data URI below the inline API limit."""
    if isinstance(value, PILImage.Image):
        image = value.copy()
    elif isinstance(value, dict) and value.get("bytes") is not None:
        image = PILImage.open(BytesIO(value["bytes"])).copy()
    elif isinstance(value, dict) and value.get("path"):
        image = PILImage.open(value["path"]).copy()
    else:
        raise TypeError(f"Unsupported image value: {type(value).__name__}")

    image = image.convert("RGB")
    image.thumbnail((1648, 2048), PILImage.Resampling.LANCZOS)

    quality = 88
    while True:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = buffer.getvalue()
        if len(encoded) <= MAX_INLINE_BYTES or quality <= 45:
            break
        quality -= 8

    # Nemotron Parse supports inline base64 images. Large images require the
    # separate NVCF asset upload flow; this keeps the batch job self-contained.
    payload = base64.b64encode(encoded).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


def extract_text(parsed: Any) -> str:
    """Flatten Nemotron Parse markdown_bbox output into readable text."""
    if isinstance(parsed, str):
        return LAYOUT_TAG_RE.sub("", parsed).strip()
    if isinstance(parsed, dict):
        if isinstance(parsed.get("text"), str):
            return extract_text(parsed["text"])
        if isinstance(parsed.get("content"), str):
            return extract_text(parsed["content"])
        for key in ("data", "results", "detections", "items"):
            if key in parsed:
                return extract_text(parsed[key])
    if isinstance(parsed, list):
        parts = []
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(extract_text(item["text"]))
            else:
                text = extract_text(item)
                if text:
                    parts.append(text)
        return "\n\n".join(part for part in parts if part)
    return ""


def parse_image(
    image_data_uri: str,
    api_key: str,
    api_url: str,
    model: str,
    timeout: int = 180,
    retries: int = 3,
) -> tuple[str, dict[str, Any]]:
    """Call Nemotron Parse and return extracted text plus raw API response."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this document image in reading order. "
                        "Return only the transcribed text, without commentary.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_uri},
                    }
                ],
            }
        ],
        "temperature": 0.0,
        "stream": False,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            raw = response.json()
            message = raw["choices"][0]["message"]
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                arguments = json.loads(tool_calls[0]["function"]["arguments"])
                text = extract_text(arguments)
            else:
                text = extract_text(message.get("content", ""))
            if not text:
                raise ValueError("Parse API returned no extractable text")
            return text, raw
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)

    raise RuntimeError(f"Nemotron Parse request failed: {last_error}") from last_error


def parse_settings(api_url: str | None = None, model: str | None = None) -> tuple[str, str, str]:
    """Dedicated parsers use their own optional key, never the Token Factory key."""
    dedicated_url = api_url or os.getenv("PARSE_API_URL")
    base = os.getenv("NEBIUS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = dedicated_url or f"{base}/chat/completions"
    key = os.getenv("PARSE_API_KEY", "") if dedicated_url else os.getenv("NEBIUS_API_KEY", "")
    if not dedicated_url and not key:
        raise ValueError("NEBIUS_API_KEY is not set. Configure it in .env or as an environment variable.")
    model = model or os.getenv("PARSE_MODEL", "")
    if not model.strip():
        raise ValueError("Set PARSE_MODEL in .env or pass --model with the exact parser model ID.")
    return url, model, key


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, help="reproducible sample")
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir", default=".hf_cache")
    parser.add_argument("--output-dir", default=".data/nemotron_parse")
    parser.add_argument("--api-url")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1")
    try:
        args.api_url, args.model, api_key = parse_settings(args.api_url, args.model)
    except ValueError as exc:
        parser.error(str(exc))

    output_dir = Path(args.output_dir)
    text_dir = output_dir / "text"
    output_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "records.jsonl"

    rows = sample_rows(
        iter_rows(
            split=args.split,
            cache_dir=args.cache_dir,
            streaming=True,
            decode_images=False,
        ),
        args.count,
        rng=random.Random(args.seed),
    )

    with records_path.open("w", encoding="utf-8") as records:
        for position, row in enumerate(rows, start=1):
            record_id = str(row["id"])
            result: dict[str, Any] = {
                "id": record_id,
                "label": LABEL_NAMES.get(int(row["label"]), str(row["label"])),
                "meta": row.get("meta", ""),
                "position": position,
            }
            try:
                text, raw = parse_image(
                    image_to_data_uri(row["image"]),
                    api_key=api_key,
                    api_url=args.api_url,
                    model=args.model,
                    timeout=args.timeout,
                )
                result["text"] = text
                result["raw_response"] = raw
                # Dataset IDs can identify a volume rather than a unique page.
                filename = f"{position:03d}_{record_id}.txt"
                result["text_file"] = f"text/{filename}"
                (text_dir / filename).write_text(
                    text + "\n", encoding="utf-8"
                )
                print(f"[{position}/{args.count}] parsed {record_id}", flush=True)
            except Exception as exc:
                result["error"] = str(exc)
                print(f"[{position}/{args.count}] failed {record_id}: {exc}", flush=True)

            records.write(json.dumps(result, ensure_ascii=False) + "\n")
            records.flush()

    print(f"Wrote {records_path}")


if __name__ == "__main__":
    main()
