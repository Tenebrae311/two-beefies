"""Check an agent's inline citations against what its tools actually returned."""

import re

CITE_RE = re.compile(r"\b(EB|WP):([A-Za-z0-9_.\-]+)")


def cited_ids(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for prefix, row_id in CITE_RE.findall(text or ""):
        seen[f"{prefix}:{row_id.rstrip('.')}"] = None
    return list(seen)


def check(text: str, retrieved: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """Return (citations backed by a retrieved source, cite ids never retrieved)."""
    backed, unsupported = [], []
    for cid in cited_ids(text):
        if cid in retrieved:
            backed.append(retrieved[cid])
        elif not any(r.startswith(cid + "-") for r in retrieved):  # page-level id "EB:1003"
            unsupported.append(cid)
    return backed, unsupported
