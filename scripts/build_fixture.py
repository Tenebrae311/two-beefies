"""Build a small development LanceDB so the agent can run before team 1's index exists.

Britannica: every page of the NLS trial volume (1st edition, 1771, Vol. 1, A-B), parsed
from ALTO OCR. Wikipedia: matching articles fetched from the MediaWiki API (plain-text
extracts, NOT the Structured Contents dump - fixture only). Vectors are filled via the
embedding NIM when EMBED_URL is set, otherwise zeros (the agent then uses full-text search).

Usage:
  curl -L -o data/nls-trial/trial.zip \
    https://nlsfoundry.s3.amazonaws.com/trial/nls-trial-encyclopaediaBritannica.zip
  unzip -q data/nls-trial/trial.zip -d data/nls-trial/extracted
  uv run python scripts/build_fixture.py data/nls-trial/extracted/encyclopaedia-britannica-sample/144133901
"""

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import httpx
import lancedb
from lancedb.index import FTS

from two_beefies import config
from two_beefies.schema import EMBED_DIM, BritannicaChunk, Match, WikipediaChunk

WIKI_TITLES = [
    "Astronomy", "Planet", "Solar System", "Comet", "Atmosphere of Earth", "Air", "Africa",
    "Americas", "Anatomy", "Agriculture", "Algebra", "Arithmetic", "Architecture", "Bee",
    "Blood", "Botany", "Barometer", "Brain", "Bread", "Alchemy", "Acid", "Abyssinia",
    "Ethiopian Empire", "Aberration of light", "Bleeding", "Bloodletting",
]
CHUNK_CHARS = 2000
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "two-beefies-fixture/0.2 (Nebius x NVIDIA Nemotron hackathon; low-volume)"}
CACHE = config.ROOT / "data" / "wiki-cache"

ALTO_NS = {"a": "http://www.loc.gov/standards/alto/v3/alto.xsd"}
HEADWORD_RE = re.compile(r"^([A-Z][A-Z\-]{2,})[,.]", re.M)


def chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    paras, out, cur = text.split("\n"), [], ""
    for p in paras:
        if cur and len(cur) + len(p) > size:
            out.append(cur.strip())
            cur = ""
        cur += p + "\n"
    if cur.strip():
        out.append(cur.strip())
    return out


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
        print(f"  embedded {len(vecs)}/{len(texts)}", flush=True)
    return vecs


def alto_text(path: Path) -> str:
    root = ET.parse(path).getroot()
    lines = []
    for line in root.iterfind(".//a:TextLine", ALTO_NS):
        words = [s.get("CONTENT", "") for s in line.iterfind("a:String", ALTO_NS)]
        lines.append(" ".join(w for w in words if w))
    return "\n".join(lines)


def britannica_rows(volume_dir: Path) -> list[dict]:
    vol_id = volume_dir.name
    mets = (volume_dir / f"{vol_id}-mets.xml").read_text(encoding="utf-8")
    year = int(re.search(r"<mods:dateIssued>(\d{4})", mets).group(1))
    volume_label = re.search(r"<mods:partName>([^<]+)", mets).group(1)
    edition = volume_label.split(" edition")[0].lower().replace("first", "1st")
    rows = []
    for m in re.finditer(r'<div ID="div_\d+" LABEL="([^"]*)" TYPE="PAGE" ORDER="(\d+)">'
                         r'<fptr FILEID="file_(\d+)\.', mets):
        label, seq, page_id = m.group(1), int(m.group(2)), m.group(3)
        alto = volume_dir / "alto" / f"{page_id}.34.xml"
        if not alto.exists():
            continue
        text = alto_text(alto)
        if len(text) < 200:
            continue
        heads = list(dict.fromkeys(HEADWORD_RE.findall(text)))[:4]
        title = f"{label}" + (f" - {', '.join(heads)}" if heads else "")
        image_url = f"https://deriv.nls.uk/dcn30/{page_id[:4]}/{page_id[4:8]}/{page_id}.30.jpg"
        for i, chunk in enumerate(chunks(text)):
            rows.append({
                "id": f"{page_id}-{i}", "doc_id": page_id, "chunk_index": i, "title": title,
                "section": None, "text": chunk,
                "url": f"https://digital.nls.uk/encyclopaedia-britannica/archive/{page_id}", "image_url": image_url,
                "edition": edition, "year": year, "volume_label": volume_label,
                "page_id": page_id, "page_seq": seq, "embed_model": config.EMBED_MODEL,
                "headwords": heads,
            })
    return rows


def wikipedia_rows() -> list[dict]:
    rows, seen = [], set()
    for title in WIKI_TITLES:  # full-text extracts come back one page per request
        cached = CACHE / f"{title}.json"
        if not cached.exists():
            for attempt in range(6):
                resp = httpx.get(WIKI_API, headers=UA, timeout=60, params={
                    "action": "query", "format": "json", "formatversion": 2,
                    "prop": "extracts|info|pageprops", "explaintext": 1,
                    "exsectionformat": "wiki", "inprop": "url", "redirects": 1, "titles": title})
                if resp.status_code == 200 and resp.content.startswith(b"{"):
                    break
                time.sleep(5 * (attempt + 1))  # rate limited (429)
            resp.raise_for_status()
            CACHE.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(resp.content)
            time.sleep(1)
        p = json.loads(cached.read_text())["query"]["pages"][0]
        if p.get("pageid") in seen:
            continue
        seen.add(p.get("pageid"))
        if not p.get("extract"):
            print(f"  {title}: missing", flush=True)
            continue
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
                    "id": f"{p['pageid']}-{n}", "doc_id": str(p["pageid"]), "chunk_index": n,
                    "title": p["title"], "section": section, "text": chunk,
                    "url": p.get("fullurl"), "image_url": None,
                    "wikidata_qid": p.get("pageprops", {}).get("wikibase_item"),
                    "revision_id": str(p.get("lastrevid")),
                    "date_modified": p.get("touched"), "embed_model": config.EMBED_MODEL,
                })
                n += 1
        print(f"  {p['title']}: {n} chunks", flush=True)
    return rows


def matches(eb: list[dict], wp: list[dict]) -> list[dict]:
    """Naive headword == title matches; enough to exercise find_counterparts."""
    by_title = {r["title"].lower(): r["doc_id"] for r in wp}
    out, seen = [], set()
    for r in eb:
        for h in r["headwords"]:
            wid = by_title.get(h.lower())
            if wid and (r["doc_id"], wid) not in seen:
                seen.add((r["doc_id"], wid))
                out.append({"britannica_doc_id": r["doc_id"], "wikipedia_doc_id": wid,
                            "rank": 1, "vector_score": None, "rerank_score": None,
                            "no_clear_match": False, "reason": f"headword {h} == title"})
    return out


def main(volume_dir: str) -> None:
    print("Britannica pages ...")
    eb = britannica_rows(Path(volume_dir))
    print(f"  {len(eb)} chunks")
    print("Wikipedia articles ...")
    wp = wikipedia_rows()
    m = matches(eb, wp)
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
        tbl.add(rows)
        if name != config.MATCHES_TABLE:
            tbl.create_index("text", config=FTS(), replace=True)
        print(f"wrote {name}: {len(rows)} rows")
    print(f"fixture built {date.today()} at {config.LANCEDB_URI}")


if __name__ == "__main__":
    main(sys.argv[1])
