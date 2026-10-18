"""Sample random dataset images and parse them with NVIDIA Nemotron Parse."""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import time
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image as PILImage

try:
    from src.query_dataset import LABEL_NAMES, iter_rows
except ModuleNotFoundError:  # direct invocation: python src/batch_nemotron_parse.py
    from query_dataset import LABEL_NAMES, iter_rows

DEFAULT_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-parse"
MAX_INLINE_BYTES = 180_000


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
    if isinstance(parsed, dict):
        if isinstance(parsed.get("text"), str):
            return parsed["text"].strip()
        if isinstance(parsed.get("content"), str):
            return parsed["content"].strip()
        for key in ("data", "results", "detections", "items"):
            if key in parsed:
                return extract_text(parsed[key])
    if isinstance(parsed, list):
        parts = []
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"].strip())
            else:
                text = extract_text(item)
                if text:
                    parts.append(text)
        return "\n\n".join(part for part in parts if part)
    return ""


def parse_image(
    image_data_uri: str,
    api_key: str,
    api_url: str = DEFAULT_API_URL,
    model: str = DEFAULT_MODEL,
    timeout: int = 180,
    retries: int = 3,
) -> tuple[str, dict[str, Any]]:
    """Call Nemotron Parse and return extracted text plus raw API response."""
    payload = {
        "model": model,
        "tools": [
            {"type": "function", "function": {"name": "markdown_bbox"}}
        ],
        "messages": [
            {
                "role": "user",
                "content": [
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
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

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
                return extract_text(arguments), raw
            return extract_text(message.get("content", "")), raw
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)

    raise RuntimeError(f"Nemotron Parse request failed: {last_error}") from last_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, help="reproducible sample")
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir", default=".hf_cache")
    parser.add_argument("--output-dir", default=".data/nemotron_parse")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise SystemExit(
            "NVIDIA_API_KEY is not set. Configure it as an environment variable "
            "or a Nebius SecretStash secret; do not put it in Git."
        )

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
                (text_dir / f"{record_id}.txt").write_text(
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
