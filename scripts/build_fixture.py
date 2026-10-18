"""Build a development LanceDB from the challenge dataset until team 1's index exists.

Britannica: a seeded random sample of pages from
NationalLibraryOfScotland/encyclopaedia_britannica_illustrated (2,573 page scans,
editions 1-8). Page images go to data/pages/<page_index>.jpg (served by the API), text
comes from two_beefies.ocr (Nemotron Parse if PARSE_URL is set, else Nemotron VL, else
Tesseract) and is cached in data/ocr/.
Wikipedia: for the headwords found on each page, the best MediaWiki search hit (plain-text
extract; fixture only - the real pipeline uses Wikipedia Structured Contents).
Vectors come from the embedding NIM when EMBED_URL is set, otherwise zeros (the agent
then uses full-text search).

Usage: uv run python scripts/build_fixture.py [--n 30] [--seed 42] [--ocr auto|parse|vl|tesseract]
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
HEADWORD_RE = re.compile(r"^\W*([A-Z][A-Z\-]{3,})\b[,.]", re.M)
NOT_HEADWORDS = {"PLATE", "FIG", "VOL", "PART", "BOOK", "CHAP", "SECT", "THE", "AND"}


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


def headwords(text: str) -> list[str]:
    found = [h for h in HEADWORD_RE.findall(text) if h not in NOT_HEADWORDS]
    return list(dict.fromkeys(found))


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not config.EMBED_URL:
        return [[0.0] * EMBED_DIM for _ in texts]
    from two_beefies.retrieval import _nim_headers, _nim_url
    vecs = []
    for i in range(0, len(texts), 16):
        resp = httpx.post(_nim_url(config.EMBED_URL, "embeddings"), headers=_nim_headers(),
                          json={"model": config.EMBED_MODEL, "input": texts[i:i + 16],
                                "input_type": "passage", "modality": "text",
                                "truncate": "END"}, timeout=120)
        resp.raise_for_status()
        vecs += [d["embedding"] for d in resp.json()["data"]]
    return vecs


def britannica_rows(n: int, seed: int, backend: str) -> list[dict]:
    ds = load_dataset(config.BRITANNICA_DATASET, split="train", cache_dir=config.HF_CACHE)
    ds = ds.cast_column("image", DatasetImage(decode=False))
    sample = sorted(random.Random(seed).sample(range(len(ds)), n))
    print(f"sampled {n} of {len(ds)} pages (seed {seed}): {sample}")
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
        heads = headwords(text)
        edition, year = edition_of(rec["meta"])
        print(f"  page {idx}: {edition}, {len(text)} chars, headwords {heads[:5]}", flush=True)
        for i, chunk in enumerate(chunks(text)):
            if len(chunk) < 40:
                continue
            rows.append({
                "id": f"{idx}-{i}", "doc_id": str(idx), "chunk_index": i, "page_index": idx,
                "volume_id": str(rec["id"]), "meta": rec["meta"],
                "illustrated": int(rec["label"]) == 1,
                "title": ", ".join(heads[:4]) or None, "section": None, "text": chunk,
                "url": f"https://huggingface.co/datasets/{config.BRITANNICA_DATASET}"
                       f"/viewer/default/train?row={idx}",
                "image_url": f"/api/page-image/{idx}", "edition": edition, "year": year,
                "volume_label": volume_label(rec["meta"]), "ocr_model": backend,
                "embed_model": config.EMBED_MODEL, "headwords": heads,
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


def wiki_article(headword: str) -> dict | None:
    """Best search hit for a headword, cached on disk."""
    cached = WIKI_CACHE / f"search-{headword.lower()}.json"
    if not cached.exists():
        WIKI_CACHE.mkdir(parents=True, exist_ok=True)
        data = _wiki_get({"generator": "search", "gsrsearch": headword.title(), "gsrlimit": 1,
                          "prop": "extracts|info|pageprops", "explaintext": 1,
                          "exsectionformat": "wiki", "inprop": "url"})
        cached.write_text(json.dumps(data))
    pages = json.loads(cached.read_text()).get("query", {}).get("pages", [])
    return pages[0] if pages and pages[0].get("extract") else None


def wikipedia_rows(eb: list[dict], per_page: int) -> tuple[list[dict], list[dict]]:
    rows, matches, seen = [], [], set()
    pages: dict[str, list[str]] = {}
    for r in eb:
        pages.setdefault(r["doc_id"], r["headwords"])
    for doc_id, heads in pages.items():
        for rank, head in enumerate(heads[:per_page], start=1):
            p = wiki_article(head)
            if p is None:
                matches.append({"britannica_doc_id": doc_id, "wikipedia_doc_id": None,
                                "rank": rank, "no_clear_match": True,
                                "reason": f"no Wikipedia search hit for headword {head}"})
                continue
            matches.append({"britannica_doc_id": doc_id, "wikipedia_doc_id": str(p["pageid"]),
                            "rank": rank, "no_clear_match": False,
                            "reason": f"headword {head} -> search hit '{p['title']}'"})
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
    return rows, matches


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="number of Britannica pages")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ocr", default="auto", choices=["auto", *ocr.BACKENDS])
    ap.add_argument("--wiki-per-page", type=int, default=2, help="headwords looked up per page")
    args = ap.parse_args()

    print("Britannica pages ...")
    eb = britannica_rows(args.n, args.seed, args.ocr)
    print("Wikipedia articles ...")
    wp, m = wikipedia_rows(eb, args.wiki_per_page)
    for rows in (eb, wp):
        for r, v in zip(rows, embed_passages([r["text"] for r in rows])):
            r["vector"] = v
    for r in eb:
        r.pop("headwords")

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
