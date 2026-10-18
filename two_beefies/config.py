"""Runtime configuration, loaded from `.env` in the repo root."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Keep Hermes state (sessions, logs, memory) inside the repo instead of ~/.hermes.
os.environ.setdefault("HERMES_HOME", str(ROOT / "hermes_home"))

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
AGENT_MODEL = os.getenv("AGENT_MODEL", "nvidia/Nemotron-3.5-Super-VL")

EMBED_URL = os.getenv("EMBED_URL", "").rstrip("/")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2")
RERANK_URL = os.getenv("RERANK_URL", "").rstrip("/")
RERANK_MODEL = os.getenv("RERANK_MODEL", "nvidia/llama-nemotron-rerank-vl-1b-v2")
NIM_API_KEY = os.getenv("NIM_API_KEY", "")

def nim_api_key(url: str) -> str:
    """Reuse the account key only for the official HTTPS Token Factory endpoint."""
    if NIM_API_KEY:
        return NIM_API_KEY
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname == "api.tokenfactory.nebius.com":
        return NEBIUS_API_KEY
    return ""


NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")  # hosted Nemotron Parse (team 1 script)
PARSE_URL = (os.getenv("PARSE_API_URL") or os.getenv("PARSE_URL", "")).rstrip("/")
PARSE_MODEL = os.getenv("PARSE_MODEL", "nvidia/nemotron-parse")
PARSE_API_KEY = os.getenv("PARSE_API_KEY", "")

# Britannica pages: the challenge dataset (2,573 page scans, editions 1-8)
BRITANNICA_DATASET = "NationalLibraryOfScotland/encyclopaedia_britannica_illustrated"
HF_CACHE = os.getenv("HF_CACHE", str(ROOT / ".hf_cache"))
PAGES_DIR = Path(os.getenv("PAGES_DIR", str(ROOT / "data" / "pages")))  # <page_index>.jpg

LANCEDB_URI = os.getenv("LANCEDB_URI", "./lancedb")
if "://" not in LANCEDB_URI:  # local path: resolve relative to the repo, not the cwd
    LANCEDB_URI = str((ROOT / LANCEDB_URI).resolve())
BRITANNICA_TABLE = os.getenv("BRITANNICA_TABLE", "britannica_chunks")
BRITANNICA_PAGES_TABLE = os.getenv("BRITANNICA_PAGES_TABLE", "britannica_pages")
WIKIPEDIA_TABLE = os.getenv("WIKIPEDIA_TABLE", "wikipedia_chunks")
MATCHES_TABLE = os.getenv("MATCHES_TABLE", "matches")
WIKI_INDEX_PATH = os.getenv("WIKI_INDEX_PATH", str(ROOT / ".data" / "wikipedia_en.sqlite"))
WIKI_CANDIDATES_TABLE = os.getenv("WIKI_CANDIDATES_TABLE", "wikipedia_candidates")
WIKI_ANALYSIS_MODEL = os.getenv("WIKI_ANALYSIS_MODEL", "nvidia/Nemotron-3.5-Super-VL")

# Retrieval knobs
CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "20"))  # vector hits handed to the reranker
SNIPPET_CHARS = int(os.getenv("SNIPPET_CHARS", "700"))
