"""Evidence scale + anachronism detector, using the Nemotron reranker as a fact-checker.

The reranker is a cross-encoder trained to score how relevant a passage is to a query.
Here the "query" is a claim an agent made and the passages are the sources it cited, so
the score says how well the cited text actually backs the claim - independent of the
LLM's own opinion of itself.

For the Britannica scholar we additionally score each claim against Wikipedia. A claim
his own (18th/19th-century) sources do not back, but modern Wikipedia does, means he
smuggled in modern knowledge: an anachronism.
"""

import math
import re
from concurrent.futures import ThreadPoolExecutor

from two_beefies import config, grounding, retrieval

# Thresholds on sigmoid(logit); calibrated on the fixture (scripts/calibrate_evidence.py)
SUPPORTED = 0.5
WEAK = 0.15

_MD_RE = re.compile(r"\*\*|__|^#+\s*|^\s*[-*\d.]+\s+", re.M)
_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_CITE_ONLY_RE = re.compile(r"^(\s*\[(EB|WP):[^\]]+\][.,;]?)+\s*$")
_BRACKETS_RE = re.compile(r"\[(EB|WP):[^\]]+\]")
# The scholar quoting or answering his opponent is not him asserting modern knowledge.
_ADDRESSES_OPPONENT = re.compile(r"\b(you|your|sir|the editor|wikipedia|modern)\b", re.I)


def available() -> bool:
    return config.RERANK


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def split_claims(text: str) -> list[dict]:
    """Sentences with their inline citations; citation-only fragments join the sentence before."""
    sentences: list[str] = []
    for line in _MD_RE.sub("", text or "").splitlines():
        for sent in _SENT_RE.split(line.strip()):
            if not sent:
                continue
            if _CITE_ONLY_RE.match(sent) and sentences:
                sentences[-1] += " " + sent
            else:
                sentences.append(sent)
    claims = []
    for sent in sentences:
        plain = re.sub(r"\s+([.,;:])", r"\1", " ".join(_BRACKETS_RE.sub("", sent).split()))
        if len(plain.split()) >= 6:
            claims.append({"text": plain, "cites": grounding.cited_ids(sent)})
    return claims


def _passages(cites: list[str], retrieved: dict[str, dict]) -> list[str]:
    texts = []
    for cid in cites:
        ids = [cid] if cid in retrieved else [r for r in retrieved if r.startswith(cid + "-")]
        for i in ids:
            row = retrieval.get(i)
            if row:
                texts.append(row["text"][:4000])
    return texts


def _support(claim: str, passages: list[str]) -> float | None:
    if not passages:
        return None
    return round(_sigmoid(max(logit for _, logit in retrieval.rerank(claim, passages))), 3)


def _modern_support(claim: str) -> float | None:
    hits = retrieval.search("wikipedia", claim, k=5)
    scores = [h["rerank_score"] for h in hits if h.get("rerank_score") is not None]
    return round(_sigmoid(max(scores)), 3) if scores else None


def _score_claim(role: str, claim: dict, retrieved: dict[str, dict]) -> dict:
    own = _support(claim["text"], _passages(claim["cites"], retrieved))
    modern = _modern_support(claim["text"]) if role == "britannica" else None
    if not claim["cites"]:
        flag = "uncited"
    elif own is not None and own >= SUPPORTED:
        flag = "supported"
    elif own is not None and own >= WEAK:
        flag = "weak"
    else:
        flag = "unsupported"
    if (role == "britannica" and flag in ("uncited", "unsupported") and modern is not None
            and modern >= SUPPORTED and not _ADDRESSES_OPPONENT.search(claim["text"])):
        flag = "anachronism"
    return claim | {"support": own, "modern_support": modern, "flag": flag}


def score_turn(role: str, text: str, retrieved: dict[str, dict]) -> dict | None:
    """{support, claims} for one agent turn, or None when no reranker is configured."""
    if not available():
        return None
    claims = split_claims(text)
    with ThreadPoolExecutor(max_workers=4) as pool:
        scored = list(pool.map(lambda c: _score_claim(role, c, retrieved), claims))
    supports = [c["support"] for c in scored if c["support"] is not None]
    return {"support": round(sum(supports) / len(supports), 3) if supports else None,
            "claims": scored}
