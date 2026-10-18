# Knowledge Across Time: Britannica vs. Wikipedia

> **two-beefies** · Nebius Build Week Hackathon × NVIDIA (Nemotron Agentic AI Challenge)

What did the world know in 1771, and what changed by 2026? This project puts historical pages of the
**Encyclopaedia Britannica** (1st–8th editions, 1768–1860) next to modern **Wikipedia** and lets AI agents argue
about the difference.

| Mode       | What happens                                                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Debate** | A *Britannica scholar* (can only search Britannica) debates a *Wikipedia editor* (can only search Wikipedia). A *moderator* rules on every point: **agreed** or **disputed**, and whether the change is one of **language**, **knowledge**, **perspective**, or has **no counterpart**. |
| **Ask**    | One Hermes agent answers a question with cited evidence from both encyclopaedias.                                                                                                                                                    |
| **Cases**  | Six documented agent runs (three successes, three failures), each traced back to the pipeline stage that made or broke it.                                                                                                          |

## Contents

- [Highlights](#highlights)
- [How the models are used](#how-the-models-are-used)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running](#running)
- [Data pipeline](#data-pipeline)
- [Dataset tools](#dataset-tools)
- [Repository layout](#repository-layout)
- [Dataset and licences](#dataset-and-licences)

## Highlights

- **Evidence scale and anachronism detector.** The Nemotron reranker works as an independent fact-checker: it scores
  each claim against the passages it cites. When the Britannica scholar says something that his 1768–1860 sources do
  not support but modern Wikipedia does, the claim is flagged as an **anachronism**, i.e. modern knowledge leaking
  into the old encyclopaedia.
- **Vision witness.** OCR text is only a lossy reading of the page, so agents can go back to the scan itself. For
  example, they can read the plate label *"CERVUS. Camelopardalis"* (the giraffe filed among the deer) and compare a
  1790s engraving with today's Wikipedia photo.
- **Grounded citations.** Every tool result carries a citation id (`EB:<row id>` / `WP:<row id>`) and agents must cite
  inline. `two_beefies/grounding.py` checks each cited id against the ids the agent's tools actually returned. Ids that
  were never retrieved are flagged as **unsupported**, shown in red in the UI and counted in the case studies.
- **Failure typology with counter-checks.** Each documented failure is attributed to a pipeline stage (Parse/OCR,
  Retrieval, Rerank, Agent reasoning, Grounding) and backed by a counter-check (`scripts/ablation_ocr.py`,
  `scripts/eval_retrieval.py`).

## How the models are used

| Component | Where | Role |
| --- | --- | --- |
| **Nemotron 3.5 Super VL** (Nebius Token Factory) | `two_beefies/agents.py`, `vision.py` | The LLM behind all four Hermes roles (qa, britannica, wikipedia, moderator). As a **vision witness** it inspects original scans (`inspect_page_image`) and compares an 18th-century engraving with the modern Wikipedia image (`compare_images`). |
| **Hermes Agent v0.22.2** | `two_beefies/agents.py`, `hermes_tools.py` | Agent loop and tool calling. Each role is its own `AIAgent` with its own toolsets. |
| **Nemotron Embed VL** (organizers' model service on a Nebius GPU VM) | `two_beefies/retrieval.py::embed` | 2048-d embeddings: `input_type=document` when indexing, `query` when searching. |
| **Nemotron Rerank VL** (same model service) | `two_beefies/retrieval.py::rerank`, `evidence.py` | Reranks the top 20 vector hits down to the top k. Also the **fact-checker**: scores every claim against the sources it cites (evidence scale) and against Wikipedia (anachronism detector). |
| **Nemotron Parse** | `src/ingest_pipeline.py`, `src/batch_nemotron_parse.py` | Turns page scans into the text stored in `britannica_chunks`. |
| **Nemotron Parse / VL OCR** | `two_beefies/ocr.py` | Dev fixture: page text via the Parse client, else Nemotron VL transcription (scans upscaled 600 → 1500 px, generation loops cut). |
| **LanceDB** | `two_beefies/retrieval.py`, `schema.py` | The `britannica_chunks`, `wikipedia_chunks` and `matches` tables. |

## Quick start

**Requirements:** Python 3.14 (Hermes Agent only supports 3.14), Node.js for the frontend, and optionally
[uv](https://docs.astral.sh/uv/). Hermes is not on PyPI, so it is cloned into `vendor/` first.

**With uv:**

```bash
./scripts/setup.sh            # clones Hermes Agent v0.22.2 into vendor/, runs uv sync and npm install
```

**With pip:**

```bash
git clone --depth 1 --branch v0.22.2 https://github.com/NousResearch/hermes-agent.git vendor/hermes-agent
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt               # installs vendor/hermes-agent + this project
cd frontend && npm install
```

Both routes install the same dependencies (listed in `pyproject.toml`). With pip, drop the `uv run` prefix from the
commands below.

**Just want to see the UI?** No backend or keys needed:

```bash
cd frontend && npm run dev     # then open http://localhost:3000/?mock=1&topic=Astronomy
```

## Configuration

Copy `.env.example` to `.env` and fill it in. Every field is explained in the file. The important ones:

| Variable | Needed for |
| --- | --- |
| `NEBIUS_API_KEY` | **Required.** Nemotron 3.5 Super VL for all agents and the vision tools. |
| `PARSE_API_URL` (alias `PARSE_URL`), `PARSE_API_KEY`, `PARSE_MODEL` | Nemotron Parse endpoint for OCR. Alternatively `NVIDIA_API_KEY` for NVIDIA's hosted Parse. |
| `RETRIEVAL_BASE_URL` | Embedding + rerank service. If empty, agents fall back to LanceDB full-text search without reranking or evidence scores. |
| `LANCEDB_URI` | Vector database location (default `./lancedb`). |

`hermes_home/` is used as `HERMES_HOME`, so Hermes state stays inside the repository. Its `config.yaml` disables
Hermes' tool-search bridge, so the model sees the retrieval tools directly.

> **Never commit API keys.** `.env` is gitignored. For cloud jobs, provide keys as secret environment variables.

## Running

```bash
# Backend
uv run python -m two_beefies.retrieval britannica "planets"            # retrieval only
uv run python -m two_beefies.qa "What does the Britannica say about <topic>, and what changed?"
uv run python -m two_beefies.debate "Astronomy"                        # debate in the terminal
uv run uvicorn two_beefies.api:app --port 8000                          # API for the frontend

# Frontend (see frontend/README.md)
cd frontend && npm run dev                                              # UI on :3000

# Evaluation
uv run python scripts/run_cases.py                                      # candidate cases + metrics -> docs/cases/
uv run python scripts/ablation_ocr.py --pages 8                         # counter-check: scan resolution vs. OCR loops
uv run python scripts/eval_retrieval.py                                 # counter-check: retrieval with/without rerank
```

The frontend has a **mock mode** (`?mock=1`) that replays a recorded debate and works fully offline. If the backend is
unreachable, it falls back to the recording automatically.

## Data pipeline

### Development fixture

For quick local development, build a small seeded fixture:

```bash
uv run python scripts/build_fixture.py --n 30 --seed 42
```

This samples 30 pages from the dataset and then:

- saves the scans to `data/pages/` (served by `/api/page-image/<page_index>`);
- reads the text with **Nemotron Parse** if `PARSE_API_URL` or `NVIDIA_API_KEY` is set, otherwise falls back to
  Nemotron VL and then Tesseract (text is cached in `data/ocr/`);
- looks up Wikipedia articles for the headwords found on each page (MediaWiki API, fixture only).

The dataset has no page ids, so a page is identified by its row index (`page_index`).

### Full ingestion

The ingestion pipeline in `src/` builds the real index. Run all commands from the repository root:

| Step | Command | What it does |
| --- | --- | --- |
| 1 | `python -m src.ingest_pipeline --count 100` | Sample pages → Nemotron Parse → passage embeddings → Britannica LanceDB table. |
| 2 | `python -m src.build_wikipedia_index --source <enwiki parquet>` | Build a reusable SQLite/FTS5 Wikipedia index from downloaded Kaggle enwiki Parquet files. `src.build_remote_wikipedia_index` indexes remote title/description metadata only, without downloading the dump. |
| 3 | `python -m src.match_wikipedia --run-dir <run>` | LLM-guided Wikipedia shortlist for existing OCR, independent of embeddings. |
| 4 | `python -m src.finalize_matches --run-dir <run>` | Embed saved pages and their shortlist, then persist one top match per page. |

Helpers: `src.run_small_pipeline` runs a bounded end-to-end pass (two pages by default, with checkpoints), and
`src.complete_parsed_run` finishes a saved sampling run concurrently. The pipeline refuses to run without
`RETRIEVAL_BASE_URL`, because it never stores placeholder vectors.

## Dataset tools

Standalone utilities for exploring the source dataset.

**Query the dataset** (output is JSON with id, label, metadata and image size):

```bash
python src/query_dataset.py --limit 5                       # first 5 rows
python src/query_dataset.py --text "Sculpture" --limit 10   # search bibliographic metadata
python src/query_dataset.py --label illustrated --limit 10  # illustrated pages only
python src/query_dataset.py --id 193469392 --limit 10       # exact record id
```

Or from Python. `query_rows` streams by default, so the dataset is never fully loaded into memory:

```python
from src.query_dataset import query_rows

for row in query_rows(text="Sculpture", label="illustrated", limit=5):
    print(row["id"], row["meta"])
```

For image processing, use `iter_rows()` from the same module; each result also contains the image object.

**OCR one random page with Tesseract** (reservoir sampling, uniform):

```bash
python src/random_image_to_text.py --seed 42 --save-image .data/random.jpg --output .data/random.json
```

This requires the Tesseract binary on your `PATH` in addition to `pytesseract` (Windows:
`winget install UB-Mannheim.TesseractOCR`). OCR of historical multi-column pages is best-effort.

**Batch-parse random pages with Nemotron Parse:**

```bash
python src/batch_nemotron_parse.py --count 100 --seed 42
python src/batch_nemotron_parse.py --count 100 --model nvidia/nemotron-parse
python src/batch_nemotron_parse.py --count 100 --output-dir .data/nemotron_parse_run2
```

The script samples pages uniformly without duplicates and uses the parser configured in `.env` (`PARSE_API_URL`, or
`NVIDIA_API_KEY` for NVIDIA's hosted Parse). Images are compressed to JPEG data URIs under about 180 KB so they can
be sent inline. A record is written and flushed after every image; individual API errors are logged and the run
continues. Results:

```text
.data/nemotron_parse/
├── records.jsonl       metadata, OCR text and raw API response
└── text/
    └── <id>.txt
```

## Repository layout

```text
two_beefies/     backend: config, schema (LanceDB contract), retrieval, hermes_tools, grounding, evidence,
                 vision, ocr, agents, qa, debate, api
src/             dataset queries, OCR and the ingestion pipeline
scripts/         setup.sh, build_fixture.py, run_cases.py, ablation_ocr.py, eval_retrieval.py
frontend/        Next.js UI (Debate, Ask, Cases), see frontend/README.md
docs/cases/      agent case runs, summary.md, annotations.json (3 successes, 3 failures)
docs/ablations/  counter-checks for the failure analysis
tests/           tests for src/
data/            dataset notes (data/README.md); local data is gitignored
hermes_home/     HERMES_HOME (agent state and config)
vendor/          Hermes Agent checkout (created by setup)
```

## Dataset and licences

- **Britannica:** [NationalLibraryOfScotland/encyclopaedia_britannica_illustrated](https://huggingface.co/datasets/NationalLibraryOfScotland/encyclopaedia_britannica_illustrated),
  2,573 page scans across editions 1–8. Columns: `image`, `label` (`illustrated` / `not-illustrated`), `id`, `meta`.
  The Parquet file (about 374 MB) is not stored in Git; it is downloaded from Hugging Face on first use and cached in
  `.hf_cache/`. The dataset card lists **CC0 1.0**; please credit the National Library of Scotland anyway. See
  [data/README.md](data/README.md).
- **Wikipedia:** text under **CC BY-SA**.
