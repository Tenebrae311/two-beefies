"""Counter-check for the Parse/OCR failure stage: does scan resolution cause the loops?

OCRs the same pages with Nemotron VL twice - at the dataset's native 600 px and upscaled
to 1500 px - and compares output length, generation loops and lexical diversity.
Writes docs/ablations/ocr_resolution.md.

Usage: uv run python scripts/ablation_ocr.py [--pages 8]
"""

import sys
import time

from two_beefies import config, ocr, retrieval, vision

OUT = config.ROOT / "docs" / "ablations" / "ocr_resolution.md"


def measure(image: bytes, width: int) -> dict:
    start = time.time()
    raw = ocr.ocr_vl(image, min_width=width)
    clean = ocr.strip_loops(raw)
    words = clean.split()
    return {"s": round(time.time() - start, 1), "raw": len(raw), "clean": len(clean),
            "loop": clean != raw, "diversity": round(len(set(words)) / max(1, len(words)), 2)}


def main() -> None:
    n = int(sys.argv[sys.argv.index("--pages") + 1]) if "--pages" in sys.argv else 8
    pages = [p for p in retrieval.pages() if not p["illustrated"]][:n]
    rows = ["| page | edition | 600 px: chars (raw) / loop | 1500 px: chars (raw) / loop |",
            "|---|---|---|---|"]
    loops = {600: 0, 1500: 0}
    for p in pages:
        image = vision.page_image_bytes(p["page_index"])
        r = {w: measure(image, w) for w in (600, 1500)}
        for w in r:
            loops[w] += r[w]["loop"]
        rows.append(f"| {p['page_index']} {p['title']} | {p['edition']} | "
                    + " | ".join(f"{r[w]['clean']} ({r[w]['raw']}) / {'LOOP' if r[w]['loop'] else 'ok'}"
                                 for w in (600, 1500)) + " |")
        print(rows[-1], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join([
        "# Ablation: scan resolution vs. VLM OCR", "",
        f"Model `{config.AGENT_MODEL}` (thinking off), {len(pages)} pages. The dataset scans "
        "are 600 px wide; '1500 px' upscales them (LANCZOS) before sending.", "",
        f"**Generation loops: {loops[600]}/{len(pages)} pages at 600 px vs "
        f"{loops[1500]}/{len(pages)} at 1500 px.** 'chars' is the usable text after cutting "
        "loops; raw length in brackets.", "", *rows, ""]))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
