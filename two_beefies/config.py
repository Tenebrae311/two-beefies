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

# Organizers' model service (Docker recipe): Nemotron embed + rerank behind one base URL,
# e.g. http://127.0.0.1:8000/v1 through an SSH tunnel to the GPU VM. EMBED_URL / NIM_API_KEY
# are accepted as older names for the same settings.
RETRIEVAL_BASE_URL = (os.getenv("RETRIEVAL_BASE_URL") or os.getenv("EMBED_URL", "")).rstrip("/")
RETRIEVAL_API_KEY = os.getenv("RETRIEVAL_API_KEY") or os.getenv("NIM_API_KEY", "")
EMBED_URL = RETRIEVAL_BASE_URL  # alias used by the ingestion scripts in src/
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2")
RERANK_MODEL = os.getenv("RERANK_MODEL", "nvidia/llama-nemotron-rerank-vl-1b-v2")
RERANK = bool(RETRIEVAL_BASE_URL)  # rerank search results (and score evidence)


def nim_api_key(url: str) -> str:
    """Bearer token for the model service; the Nebius account key is only ever sent to
    the official HTTPS Token Factory endpoint."""
    if RETRIEVAL_API_KEY:
        return RETRIEVAL_API_KEY
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname == "api.tokenfactory.nebius.com":
        return NEBIUS_API_KEY
    return ""


# Nemotron Parse: organizers' endpoint (PARSE_API_URL / PARSE_URL), else NVIDIA's hosted one
PARSE_URL = (os.getenv("PARSE_API_URL") or os.getenv("PARSE_URL", "")).rstrip("/")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")  # only for NVIDIA's hosted Parse
PARSE_MODEL = os.getenv("PARSE_MODEL", "nvidia/nemotron-3.5-parse")
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
