"""Nemotron 3.5 Super VL as an eye-witness: answer questions about the original scans.

Used by the inspect_page_image / compare_images tools. The OCR text is only a lossy
reading of the page; these tools let an agent go back to the image itself, e.g. to read
a word the OCR mangled or to describe an engraving, or to compare an 18th-century
plate with the modern Wikipedia image of the same subject.
"""

import hashlib
import io

import httpx
from PIL import Image

from two_beefies import config, ocr

UA = {"User-Agent": "two-beefies/0.2 (Nebius x NVIDIA Nemotron hackathon; low-volume)"}
WIKI_IMAGE_CACHE = config.ROOT / "data" / "wiki-images"

INSPECT_PROMPT = (
    "You are looking at a scanned page of the historical Encyclopaedia Britannica "
    "({edition}). Answer the question using ONLY what is visible on this page: quote "
    "printed text verbatim, describe illustrations precisely. If the page does not show "
    "the answer, say so.\n\nQuestion: {question}")

COMPARE_PROMPT = (
    "Image 1 is a page of the historical Encyclopaedia Britannica ({edition}). Image 2 is "
    "the lead image of the modern Wikipedia article '{title}'. Compare what the two "
    "images show and how they show it (subject, accuracy, conventions of depiction), "
    "using ONLY what is visible.\n\nQuestion: {question}")


def page_image_bytes(page_index: int) -> bytes:
    """Scan of a Britannica page: data/pages/<n>.jpg, else straight from the HF dataset."""
    path = config.PAGES_DIR / f"{page_index}.jpg"
    if path.is_file():
        return path.read_bytes()
    from datasets import Image as DatasetImage
    from datasets import load_dataset
    ds = load_dataset(config.BRITANNICA_DATASET, split="train", cache_dir=config.HF_CACHE)
    data = ds.cast_column("image", DatasetImage(decode=False))[page_index]["image"]["bytes"]
    config.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def remote_image_bytes(url: str) -> bytes:
    WIKI_IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    cached = WIKI_IMAGE_CACHE / hashlib.sha1(url.encode()).hexdigest()
    if not cached.exists():
        resp = httpx.get(url, headers=UA, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        cached.write_bytes(buf.getvalue())
    return cached.read_bytes()


def ask_images(images: list[bytes], prompt: str, max_tokens: int = 700) -> str:
    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": ocr._data_url(b)}} for b in images]
    resp = httpx.post(f"{config.NEBIUS_BASE_URL}/chat/completions", timeout=180,
                      headers={"Authorization": f"Bearer {config.NEBIUS_API_KEY}"},
                      json={"model": config.AGENT_MODEL, "temperature": 0.2,
                            "max_tokens": max_tokens,
                            # same reason as in ocr.py: thinking burns the budget on images
                            "chat_template_kwargs": {"enable_thinking": False},
                            "messages": [{"role": "user", "content": content}]})
    resp.raise_for_status()
    return ocr.strip_loops((resp.json()["choices"][0]["message"]["content"] or "").strip())


def inspect_page(row: dict, question: str) -> str:
    image = page_image_bytes(int(row["page_index"]))
    return ask_images([image], INSPECT_PROMPT.format(
        edition=row.get("edition") or "unknown edition", question=question))


def compare(eb_row: dict, wp_row: dict, question: str) -> str:
    if not wp_row.get("image_url"):
        raise ValueError(f"Wikipedia article '{wp_row.get('title')}' has no image")
    images = [page_image_bytes(int(eb_row["page_index"])), remote_image_bytes(wp_row["image_url"])]
    return ask_images(images, COMPARE_PROMPT.format(
        edition=eb_row.get("edition") or "unknown edition", title=wp_row.get("title"),
        question=question), max_tokens=900)
