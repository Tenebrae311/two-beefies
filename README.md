# two-beefies — Knowledge Across Time: Britannica Meets Wikipedia

Nebius Build Week Hackathon × NVIDIA (Nemotron Agentic AI Challenge).

Compares historical Encyclopaedia Britannica pages (1768–1860) with modern Wikipedia. It has two parts:

- **Ask**: one Hermes agent answers questions with evidence from both sources.
- **Debate**: a *Britannica scholar* agent, which can only search Britannica, debates a *Wikipedia editor* agent, which can only search Wikipedia. A *moderator* agent judges every point:
  - **agreed** or **disputed**
  - **language** (same fact, different words), **knowledge** (the facts changed), **perspective** (the framing changed) or **no counterpart**

## How the required models are used (agent part)

| Component | Where | Role |
|---|---|---|
| Nemotron 3.5 Super VL (Nebius Token Factory) | `two_beefies/agents.py` | the LLM behind all four Hermes roles (qa, britannica, wikipedia, moderator) |
| Hermes Agent v0.22.2 | `two_beefies/agents.py`, `hermes_tools.py` | agent loop and tool calling. Each role is its own `AIAgent` with its own toolsets. |
| Nemotron Embed VL (NIM) | `two_beefies/retrieval.py::embed_query` | query embeddings (`input_type=query`) |
| Nemotron Rerank VL (NIM) | `two_beefies/retrieval.py::rerank` | reranks the top 20 vector hits down to the top k |
| LanceDB | `two_beefies/retrieval.py`, `schema.py` | the `britannica_chunks`, `wikipedia_chunks` and `matches` tables |
| Nemotron Parse | data pipeline (part 1) | turns page scans into the text in `britannica_chunks` |

**How answers connect to sources:** every tool result carries a citation id (`EB:<row id>` / `WP:<row id>`), and agents must cite them inline. `grounding.py` checks each cited id against the ids that the agent's tools actually returned. Ids that were never retrieved are flagged as **unsupported**, shown in red in the UI and counted in the case studies.

## Setup

```bash
./scripts/setup.sh            # clones Hermes Agent v0.22.2 into vendor/, uv sync, npm install
$EDITOR .env                  # NEBIUS_API_KEY, EMBED_URL, RERANK_URL, LANCEDB_URI
```

`hermes_home/` is used as `HERMES_HOME`, so Hermes state stays in the repo. Its `config.yaml` turns off Hermes' tool-search bridge, which means the model sees the retrieval tools directly.

### Development data (until the full index exists)

```bash
mkdir -p data/nls-trial
curl -L -o data/nls-trial/trial.zip https://nlsfoundry.s3.amazonaws.com/trial/nls-trial-encyclopaediaBritannica.zip
unzip -q data/nls-trial/trial.zip -d data/nls-trial/extracted
uv run python scripts/build_fixture.py data/nls-trial/extracted/encyclopaedia-britannica-sample/144133901
```

This creates a fixture from the 1st edition (1771), Vol. 1 (A–B): all 2,298 page chunks from the ALTO OCR, plus about 25 related Wikipedia articles from the MediaWiki API (fixture only). Without `EMBED_URL`, retrieval falls back to LanceDB full-text search.

## Run

```bash
uv run python -m two_beefies.retrieval britannica "planets"            # retrieval only
uv run python -m two_beefies.qa "How many planets did the 1771 Britannica describe?"
uv run python -m two_beefies.debate "Astronomy"                        # debate in the terminal
uv run uvicorn two_beefies.api:app --port 8000                          # API for the frontend
cd frontend && npm run dev                                              # UI on :3000 (?mock=1 works offline)
uv run python scripts/run_cases.py                                      # candidate cases -> docs/cases/runs/
```

## Layout

```
two_beefies/   config, schema (LanceDB contract), retrieval, hermes_tools, grounding, agents, qa, debate, api
scripts/       setup.sh, build_fixture.py, run_cases.py
frontend/      Next.js UI (Debate + Ask)
docs/cases/    agent case studies (3 successes, 3 failures)
```
