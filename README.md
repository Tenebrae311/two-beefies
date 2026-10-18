# Knowledge Across Time: Britannica vs. Wikipedia

*Team two-beefies · Nebius Build Week × NVIDIA, Nemotron Agentic AI Challenge*

Demo video link can be found [here:](https://tubcloud.tu-berlin.de/s/GDf3wnzyY62kKmK)

We match scanned pages of the historical **Encyclopaedia Britannica (1768–1860)** with their closest **Wikipedia** articles and let Nemotron-powered Hermes agents compare them. The creative extra is a **debate**: a *Britannica Scholar*, who can only see the old encyclopaedia, argues with a *Wikipedia Editor*, who can only see Wikipedia. A *Moderator* classifies every difference as a change in **language**, **knowledge** or **perspective**, or marks it as having **no counterpart**.

Full technical documentation (setup, configuration, pipeline, model service, layout): **[docs/technical.md](docs/technical.md)**

## Quick start

```bash
./scripts/setup.sh                                   # Hermes Agent (vendor/), Python deps, frontend deps
cp .env.example .env                                 # add NEBIUS_API_KEY (each field is explained)
uv run uvicorn two_beefies.api:app --port 8000       # backend
cd frontend && npm run dev                           # UI: http://localhost:3000  (offline demo: ?mock=1)
```

## Task 1: Match and compare historical and modern knowledge

| Requirement | Where it is |
|---|---|
| Select 100 pages and document the selection method | Uniform random sample without replacement, seed 42, from the [challenge dataset](https://huggingface.co/datasets/NationalLibraryOfScotland/encyclopaedia_britannica_illustrated). Code: [`src/ingest_pipeline.py`](src/ingest_pipeline.py); each run's `manifest.json` records the rows. Method and dataset versions: [technical docs](docs/technical.md). |
| Find the most similar Wikipedia article(s) | Nemotron 3.5 Super VL extracts topics and modern search terms per page, giving up to 50 candidates ([`src/match_wikipedia.py`](src/match_wikipedia.py), [`two_beefies/wiki_prefilter.py`](two_beefies/wiki_prefilter.py)). Embedding similarity then picks the best article per chunk ([`src/finalize_matches.py`](src/finalize_matches.py), [`two_beefies/matching.py`](two_beefies/matching.py)). |
| Explain why they are relevant matches | Per match: the LLM topics and queries that found the candidate, plus its similarity score (`wikipedia_candidates`, `matches` tables). |
| Similarities and differences (vocabulary, word frequency, topic coverage, factual claims) | Factual claims and topic coverage: per topic in the debate verdicts and Ask answers ([`docs/cases/`](docs/cases/)). ⚠️ **Not yet in the repo:** a vocabulary and word-frequency comparison over the 100 pairs, and the exported results of the 100-page run. |
| Language change vs. knowledge change | The Moderator and the Ask agent label every difference as language / knowledge / perspective / no counterpart ([`two_beefies/agents.py`](two_beefies/agents.py)). The OCR side of "language" is measured in [`docs/ablations/ocr_resolution.md`](docs/ablations/ocr_resolution.md). |
| Make missing counterparts visible | `no_clear_match` below the minimum similarity ([`two_beefies/matching.py`](two_beefies/matching.py)), and the `no_counterpart` category in verdicts and in the UI. |

## Task 2: Agent that compares the sources

| Requirement | Where it is |
|---|---|
| Hermes Agent with Nemotron 3.5 Super VL | [`two_beefies/agents.py`](two_beefies/agents.py): four roles (Ask, Scholar, Editor, Moderator), each its own `AIAgent` with its own tools ([`two_beefies/hermes_tools.py`](two_beefies/hermes_tools.py)). |
| 3 successful cases | [`plate-giraffe`](docs/cases/runs/plate-giraffe.md) · [`modern-term`](docs/cases/runs/modern-term.md) · [`time-travel`](docs/cases/runs/time-travel.md) |
| 3 failure cases | [`ambiguity-mercury`](docs/cases/runs/ambiguity-mercury.md) (wrong material) · [`long-s`](docs/cases/runs/long-s.md) (misinterprets a source) · [`aggregate-count`](docs/cases/runs/aggregate-count.md) (cannot answer reliably) |
| Where it performs well, where it struggles, what failures reveal | Annotations with pipeline stage, cause and lesson: [`docs/cases/annotations.json`](docs/cases/annotations.json). Metrics over all 16 runs: [`docs/cases/summary.md`](docs/cases/summary.md). Counter-checks: [`docs/ablations/`](docs/ablations/). Also browsable in the UI's **Cases** tab. |
| How answers connect to sources | Every claim cites `EB:`/`WP:` ids; [`two_beefies/grounding.py`](two_beefies/grounding.py) flags ids that were never retrieved. [`two_beefies/evidence.py`](two_beefies/evidence.py) scores claims against their sources with the reranker. |

## Required models

| Model | Status |
|---|---|
| Nemotron 3.5 Super VL (Token Factory) | ✅ all agents, page analysis, vision tools (scan inspection, image comparison) |
| Hermes Agent | ✅ agent loop and tool calling |
| Nemotron Parse | ✅ organizers' shared endpoint |
| LanceDB | ✅ Britannica and Wikipedia chunks, candidates, matches |
| Nemotron Embed VL / Rerank VL | ⚠️ client code ready; the organizers' model service was not deployed. Embeddings currently use the explicit `Qwen/Qwen3-Embedding-8B` fallback; without a reranker, search is not reranked and claims get no evidence scores. |
