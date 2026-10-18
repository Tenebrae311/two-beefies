"""Page image -> text for the Britannica scans.

Backends, in the order `auto` tries them:
  parse      Nemotron Parse via team 1's client (NVIDIA_API_KEY, or PARSE_URL) - the required model
  vl         Nemotron 3.5 Super VL on Token Factory, asked to transcribe the page
  tesseract  team 1's Tesseract helper (src/random_image_to_text.py)
"""

import base64
import io
import re

import httpx
from PIL import Image

from two_beefies import config

VL_PROMPT = (
    "Transcribe all printed text on this page of an 18th/19th-century encyclopaedia "
    "verbatim, in reading order (left column before right column). Keep the original "
    "spelling, including the long s as it appears. Output plain text only, no commentary. "
    "If the page has no printed text (blank page or plate back), output nothing.")


def _data_url(image_bytes: bytes, min_width: int = 1500, max_side: int = 2400) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # The dataset scans are only 600 px wide. Upscaling gives the vision encoder more
    # tiles; at 600 px the model loses its place and loops or invents text.
    if img.width < min_width:
        img = img.resize((min_width, round(img.height * min_width / img.width)),
                         Image.Resampling.LANCZOS)
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


def ocr_vl(image_bytes: bytes, min_width: int = 1500) -> str:
    resp = httpx.post(f"{config.NEBIUS_BASE_URL}/chat/completions", timeout=300,
                      headers={"Authorization": f"Bearer {config.NEBIUS_API_KEY}"},
                      # Thinking off: with reasoning on, Nemotron spends the whole token
                      # budget "reasoning" about tables and returns no transcription.
                      json={"model": config.AGENT_MODEL, "temperature": 0, "max_tokens": 3500,
                            "chat_template_kwargs": {"enable_thinking": False},
                            "messages": [{"role": "user", "content": [
                                {"type": "text", "text": VL_PROMPT},
                                {"type": "image_url",
                                 "image_url": {"url": _data_url(image_bytes, min_width)}}]}]})
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


_LOOP_RE = re.compile(r"(.{20,300}?)\1{2,}", re.S)


def strip_loops(text: str) -> str:
    """Cut generation loops ("such registers of the ... such registers of the ...").
    On the 600 px scans a VLM sometimes repeats a phrase until max_tokens; everything
    after the first loop is unreliable, so keep one copy and drop the rest."""
    m = _LOOP_RE.search(text)
    return text[:m.start() + len(m.group(1))].rstrip() + " [...]" if m else text


def ocr(image_bytes: bytes, backend: str = "auto") -> str:
    return strip_loops(BACKENDS[pick_backend(backend)](image_bytes).strip())
