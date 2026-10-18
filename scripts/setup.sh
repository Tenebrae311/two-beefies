#!/usr/bin/env bash
# One-time setup: Hermes Agent (pinned, editable), Python deps, frontend deps.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d vendor/hermes-agent ]; then
  git clone --depth 1 --branch v0.22.2 https://github.com/NousResearch/hermes-agent.git vendor/hermes-agent
fi
uv sync
[ -f .env ] || cp .env.example .env
if [ -d frontend ]; then (cd frontend && npm install); fi
echo "Done. Fill in .env (NEBIUS_API_KEY, EMBED_URL, RERANK_URL, LANCEDB_URI)."
