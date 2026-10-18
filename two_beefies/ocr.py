"""Page image -> text for the Britannica scans.

Backends, in the order `auto` tries them:
  parse      Nemotron Parse via team 1's client (NVIDIA_API_KEY, or PARSE_URL) - the required model
  vl         Nemotron 3.5 Super VL on Token Factory, asked to transcribe the page
  tesseract  team 1's Tesseract helper (src/random_image_to_text.py)
"""

import base64
import io

import httpx
from PIL import Image

from two_beefies import config

VL_PROMPT = (
    "Transcribe all printed text on this page of an 18th/19th-century encyclopaedia "
    "verbatim, in reading order (left column before right column). Keep the original "
    "spelling, including the long s as it appears. Output plain text only, no commentary.")


def _data_url(image_bytes: bytes, max_side: int = 1800) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def ocr_parse(image_bytes: bytes) -> str:
    """Team 1's Nemotron Parse client (src/batch_nemotron_parse.py), so both parts of the
    pipeline send identical requests."""
    from src.batch_nemotron_parse import DEFAULT_API_URL, image_to_data_uri, parse_image

    url = config.PARSE_URL or DEFAULT_API_URL
    if not url.endswith("/chat/completions"):
        url += "/v1/chat/completions"
    text, _raw = parse_image(image_to_data_uri({"bytes": image_bytes}),
                             api_key=config.PARSE_API_KEY if config.PARSE_URL else config.NVIDIA_API_KEY,
                             api_url=url, model=config.PARSE_MODEL)
    return text


def ocr_vl(image_bytes: bytes) -> str:
    resp = httpx.post(f"{config.NEBIUS_BASE_URL}/chat/completions", timeout=300,
                      headers={"Authorization": f"Bearer {config.NEBIUS_API_KEY}"},
                      json={"model": config.AGENT_MODEL, "temperature": 0, "max_tokens": 4096,
                            "messages": [{"role": "user", "content": [
                                {"type": "text", "text": VL_PROMPT},
                                {"type": "image_url",
                                 "image_url": {"url": _data_url(image_bytes)}}]}]})
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


def ocr_tesseract(image_bytes: bytes) -> str:
    from src.random_image_to_text import image_to_text
    return image_to_text(Image.open(io.BytesIO(image_bytes)))


BACKENDS = {"parse": ocr_parse, "vl": ocr_vl, "tesseract": ocr_tesseract}


def pick_backend(name: str = "auto") -> str:
    if name != "auto":
        return name
    if config.PARSE_URL or config.NVIDIA_API_KEY:
        return "parse"
    if config.NEBIUS_API_KEY:
        return "vl"
    return "tesseract"


def ocr(image_bytes: bytes, backend: str = "auto") -> str:
    return BACKENDS[pick_backend(backend)](image_bytes).strip()
