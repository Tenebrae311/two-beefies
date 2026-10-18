"""Build a development LanceDB from the challenge dataset until team 1's index exists.

Britannica: a seeded random sample of pages from
NationalLibraryOfScotland/encyclopaedia_britannica_illustrated (2,573 page scans,
editions 1-8). Page images go to data/pages/<page_index>.jpg (served by the API), text
comes from two_beefies.ocr (Nemotron Parse if PARSE_URL is set, else Nemotron VL, else
Tesseract) and is cached in data/ocr/.
Wikipedia: for the topics Nemotron names for each page, the best MediaWiki search hit (plain-text
extract; fixture only - the real pipeline uses Wikipedia Structured Contents).
Vectors come from the organizers' model service (Nemotron embed) when RETRIEVAL_BASE_URL is
set; otherwise they are zeros, embed_model is "none", and the agent uses full-text search.

Plates (illustrated pages) also get a Nemotron VL description of their engravings, indexed
as a separate, clearly labelled chunk.

Usage: uv run python scripts/build_fixture.py [--n 30] [--illustrated 6] [--seed 42]
                                             [--ocr auto|parse|vl|tesseract]
"""

import argparse
import json
import random
import re
import time
from datetime import date

import httpx
import lancedb
from datasets import Image as DatasetImage
from datasets import load_dataset
from lancedb.index import FTS

from two_beefies import config, ocr
from two_beefies.schema import EMBED_DIM, BritannicaChunk, Match, WikipediaChunk

CHUNK_CHARS = 2000
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "two-beefies-fixture/0.2 (Nebius x NVIDIA Nemotron hackathon; low-volume)"}
DATA = config.ROOT / "data"
OCR_CACHE = DATA / "ocr"
WIKI_CACHE = DATA / "wiki-cache"

EDITIONS = {  # edition -> (label, first year, last year)
    "First": ("1st", 1768, 1771), "Second": ("2nd", 1778, 1783), "Third": ("3rd", 1788, 1797),
    "Fourth": ("4th", 1801, 1810), "Fifth": ("5th", 1815, 1817), "Sixth": ("6th", 1820, 1823),
    "Seventh": ("7th", 1830, 1842), "Eighth": ("8th", 1853, 1860),
}
SUPPLEMENTS = {"EB.7": ("3rd suppl.", 1801, 1803), "EB.8": ("3rd suppl.", 1801, 1803),
               "EB.12": ("4th-6th suppl.", 1815, 1824), "EB.13": ("4th-6th suppl.", 1815, 1824),
               "EB.14": ("4th-6th suppl.", 1815, 1824)}
PLATE_PROMPT = (
    "This is a plate (engraving page) from the historical Encyclopaedia Britannica. "
    "Describe every figure on it: what it depicts, labels/figure numbers you can read, "
    "and the subject area. Plain prose, at most 150 words.")
TOPIC_PROMPT = """This is OCR text of one page of the historical Encyclopaedia Britannica.
Reply with ONLY a JSON object:
{"title": "<the article(s) on this page, modern English, at most 6 words>",
 "topics": ["<1-3 English Wikipedia article titles that best match the page content>"]}

Page text:
"""


def edition_of(meta: str) -> tuple[str | None, int | None]:
    shelf = meta.rsplit(" - ", 1)[-1].strip()
    if shelf in SUPPLEMENTS:
        label, y0, y1 = SUPPLEMENTS[shelf]
        return f"{label} ({y0}-{y1})", y0
    m = re.search(r"(\w+) edition", meta)
    if m and m.group(1) in EDITIONS:
        label, y0, y1 = EDITIONS[m.group(1)]
        return f"{label} ({y0}-{y1})", y0
    return None, None


def volume_label(meta: str) -> str:
    parts = meta.split(" - ")
    return " - ".join(parts[1:-1]) if len(parts) > 2 else meta


def chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    out, cur = [], ""
    for line in text.split("\n"):
        if cur and len(cur) + len(line) > size:
            out.append(cur.strip())
            cur = ""
        cur += line + "\n"
    if cur.strip():
        out.append(cur.strip())
    return out


def page_topics(idx: int, text: str) -> dict:
    """Title + Wikipedia search terms for a page, from Nemotron (cached). Most pages are
    continuations of long treatises without a printed headword, so a regex is not enough."""
    cached = OCR_CACHE / f"{idx}.topics.json"
    if not cached.exists():
        resp = httpx.post(f"{config.NEBIUS_BASE_URL}/chat/completions", timeout=120,
                          headers={"Authorization": f"Bearer {config.NEBIUS_API_KEY}"},
                          json={"model": config.AGENT_MODEL, "temperature": 0, "max_tokens": 200,
                                "chat_template_kwargs": {"enable_thinking": False},
                                "messages": [{"role": "user",
                                              "content": TOPIC_PROMPT + text[:4000]}]})
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"] or ""
        match = re.search(r"\{.*\}", content, re.S)
        cached.write_text(match.group(0) if match else "{}")
    try:
        data = json.loads(cached.read_text())
    except json.JSONDecodeError:
        data = {}
    return {"title": data.get("title"), "topics": [t for t in data.get("topics", []) if t][:3]}


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not config.RETRIEVAL_BASE_URL:
        return [[0.0] * EMBED_DIM for _ in texts]
    from two_beefies.retrieval import embed
    vectors = []
    for i in range(0, len(texts), 64):
        vectors += embed(texts[i:i + 64], "document")
        print(f"  embedded {len(vectors)}/{len(texts)}", flush=True)
    return vectors


def plate_description(idx: int, image_bytes: bytes) -> str:
    """Nemotron VL describes an engraving so the plate becomes searchable (cached)."""
    from two_beefies import vision
    cached = OCR_CACHE / f"{idx}.plate.txt"
    if not cached.exists():
        cached.write_text(vision.ask_images([image_bytes], PLATE_PROMPT, max_tokens=400))
    return cached.read_text()


def britannica_rows(n: int, seed: int, backend: str, n_illustrated: int = 0) -> list[dict]:
    ds = load_dataset(config.BRITANNICA_DATASET, split="train", cache_dir=config.HF_CACHE)
    rng = random.Random(seed)
    sample = rng.sample(range(len(ds)), n)
    illustrated = [i for i, label in enumerate(ds["label"]) if label == 1 and i not in sample]
    plates = rng.sample(illustrated, min(n_illustrated, len(illustrated)))
    sample = sorted(sample + plates)
    ds = ds.cast_column("image", DatasetImage(decode=False))
    print(f"sampled {n} random + {len(plates)} illustrated of {len(ds)} pages (seed {seed}): "
          f"{sample}")
    config.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    backend = ocr.pick_backend(backend)
    rows = []
    for idx in sample:
        rec = ds[idx]
        image_bytes = rec["image"]["bytes"]
        (config.PAGES_DIR / f"{idx}.jpg").write_bytes(image_bytes)
        cached = OCR_CACHE / f"{idx}.{backend}.txt"
        if not cached.exists():
            cached.write_text(ocr.ocr(image_bytes, backend))
        text = cached.read_text()
        is_plate = int(rec["label"]) == 1
        if len(text) < 200 and not is_plate:  # blank pages / plate backs exist in the dataset
            print(f"  page {idx}: skipped (no text)", flush=True)
            continue
        parts = [(None, text)] if len(text) >= 40 else []
        if is_plate:
            parts.append(("illustration (described by Nemotron VL)",
                          plate_description(idx, image_bytes)))
        topics = page_topics(idx, "\n".join(t for _, t in parts))
        edition, year = edition_of(rec["meta"])
        print(f"  page {idx}: {edition}, {len(text)} chars, {topics}", flush=True)
        page_chunks = [(sec, c) for sec, t in parts for c in chunks(t) if len(c) >= 40]
        for i, (section, chunk) in enumerate(page_chunks):
            rows.append({
                "id": f"{idx}-{i}", "doc_id": str(idx), "chunk_index": i, "page_index": idx,
                "volume_id": str(rec["id"]), "meta": rec["meta"],
                "illustrated": is_plate,
                "title": topics["title"], "section": section, "text": chunk,
                "url": f"https://huggingface.co/datasets/{config.BRITANNICA_DATASET}"
                       f"/viewer/default/train?row={idx}",
                "image_url": f"/api/page-image/{idx}", "edition": edition, "year": year,
                "volume_label": volume_label(rec["meta"]), "ocr_model": backend,
                "embed_model": config.EMBED_MODEL, "topics": topics["topics"],
            })
    return rows


def _wiki_get(params: dict) -> dict:
    for attempt in range(6):
        resp = httpx.get(WIKI_API, headers=UA, timeout=60,
                         params={"action": "query", "format": "json", "formatversion": 2} | params)
        if resp.status_code == 200 and resp.content.startswith(b"{"):
            time.sleep(1)
            return resp.json()
        time.sleep(5 * (attempt + 1))  # rate limited (429)
    resp.raise_for_status()
    return {}


def wiki_article(term: str) -> dict | None:
    """Best search hit for a topic, cached on disk."""
    cached = WIKI_CACHE / f"search-{re.sub(r'[^a-z0-9]+', '-', term.lower())}.json"
    if not cached.exists():
        WIKI_CACHE.mkdir(parents=True, exist_ok=True)
        data = _wiki_get({"generator": "search", "gsrsearch": term, "gsrlimit": 1,
                          "prop": "extracts|info|pageprops", "explaintext": 1,
                          "exsectionformat": "wiki", "inprop": "url"})
        cached.write_text(json.dumps(data))
    pages = json.loads(cached.read_text()).get("query", {}).get("pages", [])
    return pages[0] if pages and pages[0].get("extract") else None


def lead_images(titles: list[str]) -> dict[str, str]:
    """Lead image URL per Wikipedia title (cached). Structured Contents has the same thing
    in its `image.content_url` column."""
    cached = WIKI_CACHE / "lead-images.json"
    known = json.loads(cached.read_text()) if cached.exists() else {}
    missing = [t for t in titles if t not in known]
    for i in range(0, len(missing), 50):
        data = _wiki_get({"titles": "|".join(missing[i:i + 50]), "prop": "pageimages",
                          "piprop": "thumbnail", "pithumbsize": 1200})
        for page in data.get("query", {}).get("pages", []):
            known[page["title"]] = page.get("thumbnail", {}).get("source")
        for t in missing[i:i + 50]:
            known.setdefault(t, None)
    WIKI_CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(known, indent=1))
    return known


def wikipedia_rows(eb: list[dict], per_page: int) -> tuple[list[dict], list[dict]]:
    rows, matches, seen = [], [], set()
    pages: dict[str, list[str]] = {}
    for r in eb:
        pages.setdefault(r["doc_id"], r["topics"])
    for doc_id, topics in pages.items():
        for rank, head in enumerate(topics[:per_page], start=1):
            p = wiki_article(head)
            if p is None:
                matches.append({"britannica_doc_id": doc_id, "wikipedia_doc_id": None,
                                "rank": rank, "no_clear_match": True,
                                "reason": f"no Wikipedia search hit for topic '{head}'"})
                continue
            matches.append({"britannica_doc_id": doc_id, "wikipedia_doc_id": str(p["pageid"]),
                            "rank": rank, "no_clear_match": False,
                            "reason": f"page topic '{head}' -> search hit '{p['title']}'"})
            if p["pageid"] in seen:
                continue
            seen.add(p["pageid"])
            section, n = "Introduction", 0
            for part in re.split(r"\n(={2,}\s*[^=]+?\s*={2,})\n", p["extract"]):
                if re.fullmatch(r"={2,}\s*[^=]+?\s*={2,}", part):
                    section = part.strip("= ")
                    continue
                if section in {"See also", "References", "Notes", "External links",
                               "Further reading", "Bibliography", "Sources"}:
                    continue
                for chunk in chunks(part):
                    if len(chunk) < 80:
                        continue
                    rows.append({
                        "id": f"{p['pageid']}-{n}", "doc_id": str(p["pageid"]),
                        "chunk_index": n, "title": p["title"], "section": section,
                        "text": chunk, "url": p.get("fullurl"), "image_url": None,
                        "wikidata_qid": p.get("pageprops", {}).get("wikibase_item"),
                        "revision_id": str(p.get("lastrevid")),
                        "date_modified": p.get("touched"), "embed_model": config.EMBED_MODEL,
                    })
                    n += 1
            print(f"  {head} -> {p['title']}: {n} chunks", flush=True)
    images = lead_images(sorted({r["title"] for r in rows}))
    for r in rows:
        r["image_url"] = images.get(r["title"])
    print(f"  lead images: {sum(1 for v in images.values() if v)}/{len(images)} articles")
    return rows, matches


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="number of Britannica pages")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ocr", default="auto", choices=["auto", *ocr.BACKENDS])
    ap.add_argument("--illustrated", type=int, default=6,
                    help="extra pages sampled from the illustrated ones (plates)")
    ap.add_argument("--wiki-per-page", type=int, default=2, help="topics looked up per page")
    args = ap.parse_args()

    print("Britannica pages ...")
    eb = britannica_rows(args.n, args.seed, args.ocr, args.illustrated)
    print("Wikipedia articles ...")
    wp, m = wikipedia_rows(eb, args.wiki_per_page)
    for rows in (eb, wp):
        for r, v in zip(rows, embed_passages([r["text"] for r in rows])):
            r["vector"] = v
            r["embed_model"] = config.EMBED_MODEL if config.RETRIEVAL_BASE_URL else "none"
    for r in eb:
        r.pop("topics")

    db = lancedb.connect(config.LANCEDB_URI)
    for name, schema, rows in ((config.BRITANNICA_TABLE, BritannicaChunk, eb),
                               (config.WIKIPEDIA_TABLE, WikipediaChunk, wp),
                               (config.MATCHES_TABLE, Match, m)):
        tbl = db.create_table(name, schema=schema, mode="overwrite")
        if rows:
            tbl.add(rows)
        if name != config.MATCHES_TABLE and rows:
            tbl.create_index("text", config=FTS(), replace=True)
        print(f"wrote {name}: {len(rows)} rows")
    print(f"fixture built {date.today()} at {config.LANCEDB_URI}")


if __name__ == "__main__":
    main()
