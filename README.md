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
src/           dataset queries + OCR (part 1, see below)
tests/         tests for src/
data/          dataset notes (data/README.md); local data is gitignored
two_beefies/   config, schema (LanceDB contract), retrieval, hermes_tools, grounding, agents, qa, debate, api
scripts/       setup.sh, build_fixture.py, run_cases.py
frontend/      Next.js UI (Debate + Ask)
docs/cases/    agent case studies (3 successes, 3 failures)
```

## Datensatz & OCR (Teil 1)

### Enthaltene Daten

Das Projekt bindet das Hugging-Face-Dataset [NationalLibraryOfScotland/encyclopaedia_britannica_illustrated](https://huggingface.co/datasets/NationalLibraryOfScotland/encyclopaedia_britannica_illustrated) ein.

Es handelt sich um 2.573 historische Bilder aus der Encyclopaedia-Britannica-Sammlung der National Library of Scotland. Jede Zeile enthält:

- `image`: Bild
- `label`: `not-illustrated` oder `illustrated`
- `id`: Datensatz-ID
- `meta`: bibliografische Metadaten

Die Parquet-Datei ist ungefähr 374 MB groß und wird deshalb nicht direkt in Git gespeichert. Stattdessen lädt der Query-Code sie bei der ersten Verwendung von Hugging Face und nutzt danach den lokalen Cache. Die Dataset Card nennt CC0 1.0 als Lizenz; bitte die Quelle bei Weiterverwendung trotzdem angeben.

### Projektstruktur

```text
.
├── data/
│   └── README.md              Herkunft, Schema und Speicherentscheidung
├── src/
│   ├── __init__.py
│   ├── query_dataset.py         Laden und Filtern des Datasets
│   └── random_image_to_text.py  Zufälliges Bild auswählen und OCR ausführen
├── tests/
│   └── test_random_image_to_text.py
├── .gitignore                 lokale Caches und Datenablagen
├── requirements.txt           Python-Abhängigkeiten
└── README.md                  Projekt- und Nutzungsdokumentation
```

### Einrichtung

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
```

### Content abfragen

Alle Beispiele aus dem Repository-Stammverzeichnis ausführen:

```bash
# Die ersten 5 Datensätze ausgeben
python src/query_dataset.py --limit 5

# Nach bibliografischen Metadaten suchen
python src/query_dataset.py --text "Sculpture" --limit 10

# Nur illustrierte Seiten
python src/query_dataset.py --label illustrated --limit 10

# Nach einer exakten Datensatz-ID suchen
python src/query_dataset.py --id 193469392 --limit 10
```

Die Ausgabe ist JSON und enthält ID, Label, Metadaten sowie die Bildabmessungen. Durch `--cache-dir .hf_cache` wird der Hugging-Face-Cache im Projektverzeichnis abgelegt; dieser Ordner ist in `.gitignore` ausgeschlossen.

### Nutzung als Python-Modul

```python
from src.query_dataset import query_rows

rows = query_rows(text="Sculpture", label="illustrated", limit=5)
for row in rows:
    print(row["id"], row["meta"])
```

`query_rows` arbeitet standardmäßig im Streaming-Modus. Dadurch muss nicht das komplette Dataset in den Arbeitsspeicher geladen werden.

### Zufälliges Bild in Text umwandeln

`src/random_image_to_text.py` wählt per Reservoir Sampling genau einen zufälligen Datenpunkt aus und führt Tesseract-OCR auf dem Bild aus:

```bash
python src/random_image_to_text.py --save-image .data/random.jpg --output .data/random.json
```

Für eine reproduzierbare Auswahl kann ein Seed angegeben werden:

```bash
python src/random_image_to_text.py --seed 42
```

Zusätzlich zu `pytesseract` muss die Tesseract-Anwendung selbst installiert und im `PATH` verfügbar sein. Auf Windows kann die Installation beispielsweise über `winget` erfolgen:

```bash
winget install UB-Mannheim.TesseractOCR
```

Die OCR-Erkennung historischer, mehrspaltiger Seiten ist nur ein Versuch und kann Nachbearbeitung benötigen. Das Script gibt neben dem erkannten Text auch `id`, Label und bibliografische Metadaten des ausgewählten Bildes aus.

## 100 zufällige Bilder mit Nemotron Parse verarbeiten

`src/batch_nemotron_parse.py` wählt 100 Bilder gleichverteilt und ohne Duplikate aus. Jedes Bild wird an NVIDIA Nemotron Parse gesendet und als Text gespeichert.

Der API-Key wird ausschließlich über die Umgebungsvariable `NVIDIA_API_KEY` gelesen. Er gehört weder in den Quellcode noch in Git. `.env` ist durch `.gitignore` ausgeschlossen; für Nebius-Jobs sollte der Wert über SecretStash als Secret-Umgebungsvariable gesetzt werden.

Windows PowerShell:

```powershell
$env:NVIDIA_API_KEY = "DEIN_KEY_NUR_LOKAL_SETZEN"
python src/batch_nemotron_parse.py --count 100 --seed 42
```

Bash:

```bash
export NVIDIA_API_KEY="DEIN_KEY_NUR_LOKAL_SETZEN"
python src/batch_nemotron_parse.py --count 100 --seed 42
```

Ergebnisse:

```text
.data/nemotron_parse/
├── records.jsonl       Metadaten, OCR-Text und API-Antwort
└── text/
    ├── <id-1>.txt
    ├── <id-2>.txt
    └── ...
```

Das Script schreibt nach jedem Bild einen Datensatz und leert den Ausgabepuffer. Bei einzelnen API-Fehlern wird mit dem nächsten Bild fortgesetzt und der Fehler in `records.jsonl` vermerkt. Die Bilder werden vor dem API-Aufruf als komprimierte JPEG-Data-URI unter ungefähr 180 KB vorbereitet, damit sie inline an die API gesendet werden können.

Optionen:

```bash
python src/batch_nemotron_parse.py --count 100 --seed 42
python src/batch_nemotron_parse.py --count 100 --model nvidia/nemotron-parse
python src/batch_nemotron_parse.py --count 100 --output-dir .data/nemotron_parse_run2
```

Den API-Key bitte nicht im Chat senden. Für die lokale Ausführung selbst als Umgebungsvariable setzen; für den Cloud-Job als Secret konfigurieren.

### Wichtiger Hinweis zu Bildern

Die Query-Ausgabe beschreibt die Treffer. Die eigentlichen Bilddaten liegen im Hugging-Face-Dataset und werden von `datasets` lokal gecacht. Für Training oder Bildverarbeitung kann `iter_rows()` aus `src/query_dataset.py` verwendet werden; dort enthält jedes Ergebnis zusätzlich das Bildobjekt.

