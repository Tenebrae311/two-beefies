"""Runtime configuration, loaded from `.env` in the repo root."""

import os
from pathlib import Path

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

LANCEDB_URI = os.getenv("LANCEDB_URI", str(ROOT / "lancedb"))
BRITANNICA_TABLE = os.getenv("BRITANNICA_TABLE", "britannica_chunks")
WIKIPEDIA_TABLE = os.getenv("WIKIPEDIA_TABLE", "wikipedia_chunks")
MATCHES_TABLE = os.getenv("MATCHES_TABLE", "matches")

# Retrieval knobs
CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "20"))  # vector hits handed to the reranker
SNIPPET_CHARS = int(os.getenv("SNIPPET_CHARS", "700"))
