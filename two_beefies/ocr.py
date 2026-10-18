"""Page image -> text for the Britannica scans.

Backends, in the order `auto` tries them:
  parse      Nemotron Parse (organizers' shared endpoint, PARSE_URL) - the required model
  vl         Nemotron 3.5 Super VL on Token Factory, asked to transcribe the page
  tesseract  team 1's Tesseract helper (src/random_image_to_text.py)
"""

import base64
import io
import json

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


def _texts(node) -> list[str]:
    """Collect every "text" field from Nemotron Parse's nested tool-call output."""
    if isinstance(node, dict):
        return ([node["text"]] if isinstance(node.get("text"), str) else []) + \
            [t for v in node.values() if isinstance(v, (dict, list)) for t in _texts(v)]
    if isinstance(node, list):
        return [t for v in node for t in _texts(v)]
    return []


def ocr_parse(image_bytes: bytes) -> str:
    headers = {"Authorization": f"Bearer {config.PARSE_API_KEY}"} if config.PARSE_API_KEY else {}
    url = config.PARSE_URL if config.PARSE_URL.endswith("/chat/completions") \
        else f"{config.PARSE_URL}/v1/chat/completions"
    resp = httpx.post(url, headers=headers, timeout=300, json={
        "model": config.PARSE_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": _data_url(image_bytes)}}]}],
        "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
        "tool_choice": {"type": "function", "function": {"name": "markdown_no_bbox"}},
    })
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    if msg.get("tool_calls"):
        args = json.loads(msg["tool_calls"][0]["function"]["arguments"])
        return "\n".join(_texts(args))
    return msg.get("content") or ""


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
    if config.PARSE_URL:
        return "parse"
    if config.NEBIUS_API_KEY:
        return "vl"
    return "tesseract"


def ocr(image_bytes: bytes, backend: str = "auto") -> str:
    return BACKENDS[pick_backend(backend)](image_bytes).strip()
