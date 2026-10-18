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

Python 3.14 is required (Hermes Agent only supports 3.14). Hermes is not installable from PyPI, so it is cloned into `vendor/` first.

**With uv:**

```bash
./scripts/setup.sh            # clones Hermes Agent v0.22.2 into vendor/, uv sync, npm install
```

**Without uv (pip):**

```bash
git clone --depth 1 --branch v0.22.2 https://github.com/NousResearch/hermes-agent.git vendor/hermes-agent
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt               # installs vendor/hermes-agent + this project (pyproject.toml)
cd frontend && npm install
```

Both ways install the same dependencies, which are listed in `pyproject.toml`. With pip, drop the `uv run` prefix from the commands below.

Then fill in `.env`, starting from `.env.example`: `NEBIUS_API_KEY`, `NVIDIA_API_KEY`, `EMBED_URL`, `RERANK_URL`, `LANCEDB_URI` (each field is explained in the file).

`hermes_home/` is used as `HERMES_HOME`, so Hermes state stays in the repo. Its `config.yaml` turns off Hermes' tool-search bridge, which means the model sees the retrieval tools directly.

### Development data (until team 1's index exists)

```bash
uv run python scripts/build_fixture.py --n 30 --seed 42
```

This samples 30 pages (seeded) from the challenge dataset [NationalLibraryOfScotland/encyclopaedia_britannica_illustrated](https://huggingface.co/datasets/NationalLibraryOfScotland/encyclopaedia_britannica_illustrated), which has 2,573 page scans across editions 1–8. The script then:

- saves the scans to `data/pages/`, served by `/api/page-image/<page_index>`
- reads the text with **Nemotron Parse**, using team 1's client in `src/batch_nemotron_parse.py`, if `NVIDIA_API_KEY` (or `PARSE_URL`) is set. Otherwise it falls back to Nemotron VL and then to Tesseract; the text is cached in `data/ocr/`.
- looks up Wikipedia articles for the headwords it finds on each page (MediaWiki API, fixture only)

The dataset has no page ids, so a page is identified by its row index (`page_index`). Without `EMBED_URL`, retrieval falls back to LanceDB full-text search.

## Run

```bash
uv run python -m two_beefies.retrieval britannica "planets"            # retrieval only
uv run python -m two_beefies.qa "What does the Britannica say about <topic>, and what changed?"
uv run python -m two_beefies.debate "Astronomy"                        # debate in the terminal
uv run uvicorn two_beefies.api:app --port 8000                          # API for the frontend
cd frontend && npm run dev                                              # UI on :3000 (?mock=1 works offline)
uv run python scripts/run_cases.py                                      # candidate cases -> docs/cases/runs/
```

## Layout

```
src/           dataset queries, OCR and ingest_pipeline (sampling -> parsing -> embeddings -> LanceDB)
tests/         tests for src/
data/          dataset notes (data/README.md); local data is gitignored
two_beefies/   config, schema (LanceDB contract), embedding, retrieval, hermes_tools, grounding, agents, qa, debate, api
scripts/       setup.sh, build_fixture.py, run_cases.py
frontend/      Next.js UI (Debate + Ask)
docs/cases/    agent case studies (3 successes, 3 failures)
```

## Datensatz & OCR (Teil 1)

### Schneller vollständiger Pipeline-Test (standardmäßig 2 Seiten)

```powershell
python -m pip install -r requirements-pipeline.txt
python -m src.run_small_pipeline --run-dir .data/ingestion/live100 --count 2 --allow-partial-index
```

Der kleine Runner verwendet bei einem vorhandenen Lauf nur die ersten zwei gespeicherten Seiten und vorhandene Parser-/LLM-Checkpoints. Bei einem neuen Laufordner wählt er standardmäßig nur zwei Bilder aus. Er führt Parsing, Nemotron-Analyse, Wikipedia-Vorauswahl, Embeddings und finale Top-1-Zuordnung nacheinander aus. Ein vorhandener Wikipedia-Metadatenindex wird vorausgesetzt; ein großer Indexaufbau oder Download wird nicht automatisch gestartet.

`--allow-partial-index` erlaubt ausdrücklich die bereits importierten Shards eines unvollständigen Indexes. Ergebnisse enthalten diese eingeschränkte Corpus-Abdeckung; sie sind keine Suche im vollständigen Wikipedia-Bestand. Ohne dieses Flag wird ein unvollständiger Index abgelehnt.

Fehlt der echte Nemotron-Embedding-Endpunkt (`EMBED_URL`), bleiben Parser-Texte, Analysen und Kandidaten erhalten. Der Lauf schreibt `small_pipeline_summary.json` mit Status `awaiting_nemotron_embedding_endpoint` und endet mit Exit-Code 2. Es werden weder ein anderes Modell noch Platzhaltervektoren eingesetzt. Nach Eintragen des Endpunkts wird derselbe Befehl fortgesetzt.

Der letzte Schritt kann separat gestartet werden:

```powershell
python -m src.finalize_matches --run-dir .data/ingestion/live100 --limit 2 --allow-partial-index
```

Er encodiert Britannica-Abschnitte und die maximal 50 Wikipedia-Kandidaten mit demselben Embedding-Modell, speichert Vektoren in `britannica_chunks`/`wikipedia_chunks` und den besten Kandidaten in `matches`. Die Bewertung ist der maximale Kosinuswert zwischen den Textabschnitten. Pro Wikipedia-Artikel werden standardmäßig höchstens acht über den Text verteilte Abschnitte berücksichtigt (`--max-article-chunks`). `--min-score` erlaubt eine Mindestähnlichkeit; darunter wird `no_clear_match` gesetzt. Geänderte OCR-Texte oder Corpus-Snapshots machen alte Kandidaten ungültig. Embeddings werden nach Modell, Endpunkt und Text gecacht.

Rohe Parser-Texte werden außerdem unabhängig vom Embedder in LanceDBs `britannica_pages` gespeichert. Der abgeschlossene Teil des großen Laufs bleibt erhalten; für den Kurztest werden keine 100 Bilder erneut verarbeitet.

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

python -m pip install -r requirements-pipeline.txt
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

## Pipeline: 100 zufällige Bilder → Parse → Embeddings → LanceDB

`src/ingest_pipeline.py` verbindet die Schritte zu einem wiederaufnehmbaren Lauf:

1. Standardmäßig **100 zufällige Dataset-Zeilen ohne Zurücklegen** auswählen und die Bilder lokal sichern.
2. Bilder mit dem dedizierten Nemotron-Parser auslesen; bereinigten Text und unveränderte API-Antworten speichern.
3. Texte in Abschnitte von maximal **2.000 Zeichen mit 200 Zeichen Überlappung** aufteilen.
4. Die Abschnitte mit **Nemotron Embed VL** als `input_type=passage` encodieren, in Batches von maximal 16 Abschnitten.
5. Echte **2.048-dimensionale Vektoren**, Text, Herkunft und Metadaten in LanceDBs `britannica_chunks` speichern. Ein Volltextindex wird zusätzlich aufgebaut; kleine Tabellen können direkt per Vektorsuche durchsucht werden.

### Konfiguration und Start

```powershell
python -m pip install -r requirements-pipeline.txt
```

In der lokalen `.env`:

```dotenv
# Dedizierter Parser, Modellkennung durch /v1/models bestätigt
PARSE_API_URL=https://port8000-kh2kceraevwe0k1.tunnel.applications.uk-south2.nebius.cloud/v1/chat/completions
PARSE_MODEL=nvidia/nemotron-3.5-parse
PARSE_API_KEY=

# Den tatsächlichen laufenden Embedding-NIM-Endpunkt eintragen
EMBED_URL=https://DEIN-EMBEDDING-ENDPUNKT
EMBED_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2
NIM_API_KEY=

LANCEDB_URI=./lancedb
BRITANNICA_TABLE=britannica_chunks
```

Der bekannte Parser benötigt beim bisherigen Test keinen Key. `PARSE_API_KEY` ist nur nötig, wenn der Parser selbst Authentifizierung verlangt. Dein `NEBIUS_API_KEY` wird nicht an einen dedizierten Parser gesendet. `NIM_API_KEY` gehört ausschließlich zur Embedding-/Reranking-Konfiguration. Tunnel-URLs können sich nach einem Deployment-Neustart ändern.

Für Embeddings/Reranking über `https://api.tokenfactory.nebius.com/v1/...` wird automatisch der vorhandene `NEBIUS_API_KEY` genutzt, sofern kein expliziter `NIM_API_KEY` gesetzt ist. An separate Deployment-/Tunnel-URLs wird der Nebius-Kontokey nicht automatisch weitergegeben. Ein Nemotron-Embed-VL-Deployment muss tatsächlich verfügbar sein; bei der zuletzt geprüften Token-Factory-Modellliste dieses Kontos war es nicht enthalten. Der Endpunkt eines separat auf Nebius betriebenen NIM kann stattdessen als `EMBED_URL` eingetragen werden.

Aus dem Repository-Stammverzeichnis:

```powershell
python -m src.ingest_pipeline --count 100 --run-dir .data/ingestion/run100
# Optional: reproduzierbare Auswahl mit --seed 42
```

Ohne `--run-dir` entsteht ein neuer Zeitstempel-Ordner. Fehlt `EMBED_URL`, stoppt die Pipeline vor Download und Parsing. Platzhalter- oder Nullvektoren werden nicht gespeichert. Ein vorhandener Index mit anderem Embedding-Modell bzw. abweichendem Schema wird abgelehnt; dafür eine separate Tabelle mit `--table` wählen. Das Query-Embedding muss dasselbe Modell verwenden wie die Pipeline (`EMBED_MODEL`).

### Zwischenstände und Fortsetzen

```text
.data/ingestion/run100/
├── manifest.json       feste Bildauswahl, Dataset-Zeilen, Metadaten und Prüfsummen
├── images/             die tatsächlich an den Parser gesendeten JPEGs
├── parsed/             bereinigte TXT-Dateien und rohe Parser-Antworten als JSON
├── events.jsonl        Erfolg/Fehler pro Bild und Verarbeitungsstufe
└── summary.json        Anzahl ausgewählter/gespeicherter Bilder, Chunks und Fehler
```

```powershell
python -m src.ingest_pipeline --resume --run-dir .data/ingestion/run100
```

Beim Fortsetzen wird die gespeicherte Auswahl verwendet, ohne das Dataset erneut zu laden. Vorhandene Parser-Antworten werden wiederverwendet, sofern Endpunkt und Parse-Modell gleich geblieben sind. Embeddings werden erneut erzeugt und per stabiler Chunk-ID aktualisiert bzw. eingefügt, statt Duplikate anzulegen. Überzählige alte Chunks desselben Dokuments werden entfernt. Fehler einzelner Bilder werden protokolliert; andere Bilder werden weiterverarbeitet. Bei Fehlern endet der Lauf mit Exit-Code 1.

Die Dataset-ID kann bei verschiedenen Seiten gleich sein. Dokument-IDs der Pipeline verwenden deshalb Dataset-Zeile und Bild-Prüfsumme. Unbekannte Seitenzahlen und Erscheinungsjahre bleiben leer, statt aus der Band-ID erfunden zu werden. Der Embedding-Zweig befüllt Britannica. Der folgende LLM-Zweig baut zusätzlich eine Wikipedia-Vorauswahl auf.

## Zweiter Zweig: LLM-Verständnis → bis zu 50 Wikipedia-Kandidaten pro Seite

```text
100 zufällige Bilder → Nemotron Parse → gespeicherter Seitentext
                                       ├─ Passage-Embeddings → britannica_chunks
                                       └─ Nemotron 3.5 Super VL
                                          → Themen, Entitäten, Suchbegriffe, moderne Synonyme
                                          → Suche im lokalen enwiki-Snapshot
                                          → bis zu 50 Artikel pro Seite → wikipedia_candidates
                                          → Embedding-Vergleich / Top-1-Match
```

Eine Britannica-Seite kann mehrere verschiedene Einträge enthalten. Das LLM analysiert deshalb bis zu acht Themen pro Seite und liefert je Thema `keywords`, `search_queries` und `suggested_titles`. Historische Schreibweisen und offensichtliche OCR-Fehler werden bei der Suche in moderne englische Begriffe überführt. Titelvorschläge sind Suchhinweise; nur Artikel, die tatsächlich im Wikipedia-Snapshot stehen, können in die Kandidatentabelle gelangen.

Die Kandidaten werden über einen **SQLite-FTS5-Volltextindex** mit BM25-Gewichtung von Titel, Beschreibung, Abstract und Artikeltext gefunden. Treffer mehrerer Suchanfragen werden per Reciprocal Rank Fusion zusammengeführt und nach Artikel-ID dedupliziert. Exakte, im Snapshot bestätigte Titelvorschläge erhalten zusätzlich Gewicht. Es entstehen maximal 50 Kandidaten **pro Britannica-Seite**, nicht 50 für alle Seiten zusammen. Bei weniger Treffern wird die Liste nicht mit erfundenen oder beliebigen Artikeln aufgefüllt. Die Relevanz dieser Vorauswahl muss anschließend durch Embeddings geprüft werden.

### 1. Suchindex aus dem verlinkten Kaggle-Datensatz aufbauen

Quelle: [Wikimedia Foundation – Wikipedia Structured Contents, enwiki](https://www.kaggle.com/datasets/wikimedia-foundation/wikipedia-structured-contents/data?select=enwiki).

Die englischen Parquet-Dateien herunterladen und lokal entpacken, beispielsweise unter `data/wikipedia/enwiki/`. Die vollständige englische Ausgabe ist laut Dataset Card etwa 34,61 GiB groß; der daraus erzeugte Text-/Suchindex benötigt zusätzlichen Speicher. Der Import liest die Dateien in Batches, ohne den gesamten Bestand in den Arbeitsspeicher zu laden.

```powershell
python -m pip install -r requirements-pipeline.txt
python -m src.build_wikipedia_index --source data/wikipedia/enwiki --index .data/wikipedia_en.sqlite
# Nach einem Abbruch: dieselben Dateien und denselben Index verwenden
python -m src.build_wikipedia_index --source data/wikipedia/enwiki --index .data/wikipedia_en.sqlite --resume
```

Das tatsächliche Structured-Contents-Schema wird verarbeitet: `identifier`, `name`, `url`, `description`, `abstract`, JSON-kodierte `sections`, `version.identifier` und `main_entity.identifier`. Französische Artikel werden ausgeschlossen. Bei mehrfach vorhandenen Artikel-IDs bleibt die neueste Revision erhalten. Artikeltext, Quell-Shard und Zeilennummer bleiben gespeichert, damit die spätere Embedding-Stufe die Kandidaten direkt aus dem Snapshot laden kann. Ein Index über nur einzelne Shards ist für Tests möglich; er durchsucht dann nur diesen Teilbestand.

In `.env` können diese Werte gesetzt werden:

```dotenv
WIKI_ANALYSIS_MODEL=nvidia/Nemotron-3.5-Super-VL
WIKI_INDEX_PATH=./.data/wikipedia_en.sqlite
WIKI_CANDIDATES_TABLE=wikipedia_candidates
```

Das LLM verwendet `NEBIUS_BASE_URL` und den bereits vorhandenen `NEBIUS_API_KEY`. Es benötigt weder den Parser-Key noch einen Embedding-Endpunkt.

### 2. Bereits geparste Texte nachträglich analysieren und Kandidaten finden

```powershell
# Gespeicherte Parser-Texte eines Pipeline-Laufs verwenden
python -m src.match_wikipedia --run-dir .data/ingestion/run100

# Alternativ: vorhandene Britannica-Seiten aus LanceDB lesen
python -m src.match_wikipedia --from-db --output-dir .data/wiki_prefilter/run100

# Alternativ: records.jsonl des früheren reinen Parser-Laufs verwenden
python -m src.match_wikipedia --records .data/nemotron_parse_test_10/records.jsonl --output-dir .data/wiki_prefilter/test10
```

`--from-db` gruppiert Chunks anhand ihrer `doc_id`; mögliche Überlappungen bleiben im LLM-Eingabetext enthalten. Vorhandene vollständige Parser-Checkpoints sind deshalb die bevorzugte Quelle. Der alte `records.jsonl`-Import erzeugt eigene stabile Dokument-IDs, weil die damaligen Dataset-IDs nicht pro Seite eindeutig waren. Er verändert keine bestehenden Britannica-Chunk-IDs.

Ohne lokalen Wikipedia-Bestand lassen sich zunächst nur die Themen und Suchbegriffe erzeugen. Beim späteren Suchlauf denselben Ausgabeordner verwenden, damit diese Analysen wiederverwendet werden:

```powershell
python -m src.match_wikipedia --from-db --analyze-only --output-dir .data/wiki_prefilter/run100
# Später, sobald der Wikipedia-Index aufgebaut ist:
python -m src.match_wikipedia --from-db --output-dir .data/wiki_prefilter/run100
```

Für einen kleinen Test kann `--limit 1` gesetzt werden. Sehr lange OCR-Texte werden anhand von vier über die Seite verteilten Ausschnitten analysiert (insgesamt maximal 24.000 Textzeichen); dies wird im Analyse-Checkpoint vermerkt.

### 3. Beide Zweige direkt nach dem Parsing ausführen

```powershell
# Sampling → Parsing → LLM/Wikipedia, noch ohne Embedding-Endpunkt möglich
python -m src.ingest_pipeline --count 100 --mode wikipedia --run-dir .data/ingestion/run100

# Sampling → Parsing → sowohl LLM/Wikipedia als auch Britannica-Embeddings
python -m src.ingest_pipeline --count 100 --mode both --run-dir .data/ingestion/run100_both
```

Bei `--mode both` werden die beiden Zweige unabhängig verarbeitet: Ein Embedding-Fehler verhindert die Wikipedia-Vorauswahl nicht und umgekehrt. Der bisherige Standard `--mode embeddings` bleibt verfügbar. Beim Fortsetzen zusätzlich `--resume` setzen.

### Ergebnisse und späteres 1:1-Matching

Im Ausgabeordner entstehen `analysis/*.json` (Zusammenfassung, Themen und Suchbegriffe, Modell und rohe LLM-Antwort), `candidates/*.json` (gefundene Artikel und Rangfolge), `events.jsonl` und `summary.json`. Die Gesamtpipeline legt dies unter `<run-dir>/wikipedia/` ab. LLM-Analysen werden bei gleichem Text, Metadaten, Modell, Endpunkt und Prompt wiederverwendet; die Suche wird gegen den aktuellen Index erneut ausgeführt.

In LanceDB speichert `wikipedia_candidates` je Kandidat die Britannica-Dokument-ID, Wikipedia-ID, Rang, lexikalischen Fusionsscore, Titel, URL, Abstract-Ausschnitt, Revision, Quellenposition und Corpus-Snapshot sowie die passenden Themen/Suchanfragen. Wiederholungen aktualisieren diese Vorauswahl dokumentweise. Unlesbare Seiten oder fehlende Treffer erhalten eine leere Vorauswahl.

Diese Tabelle enthält **Vorschläge**, noch keine bestätigten 1:1-Zuordnungen. `src.finalize_matches` encodiert diese maximal 50 Kandidaten und schreibt die Top-1-Entscheidung in `matches`. `WikipediaIndex.get(wikipedia_doc_id)` liefert dafür den vollständigen normalisierten Artikeltext; Kandidaten und Index müssen denselben `corpus_snapshot` verwenden.

### Wikipedia ohne vollständigen Dump-Download

`src.build_remote_wikipedia_index` kann alternativ nur Titel, Beschreibungen, IDs, URLs und Revisionsmetadaten per HTTP-Range-Zugriff aus dem offiziellen Wikimedia-Hugging-Face-Repository `wikimedia/structured-wikipedia` laden. Es wird eine feste Revision verwendet. Die Wikipedia-Artikeltexte bleiben zunächst remote und werden nur für ausgewählte Kandidaten geladen und unter `.data/wikipedia_article_cache/` gecacht. Das entspricht dem Structured-Contents-Datenformat des Kaggle-Datensatzes; der konkrete Snapshot wird ausdrücklich protokolliert.

Dieser Metadatenindex sucht in Titeln/Beschreibungen, nicht im gesamten Artikeltext. Auch der vollständige Metadatenindex braucht Laufzeit; er wird deshalb nur explizit aufgebaut:

```powershell
python -m src.build_remote_wikipedia_index --workers 8
python -m src.build_remote_wikipedia_index --workers 8 --resume
```

## Nur Parsing: 100 zufällige Bilder mit Nemotron Parse über Nebius verarbeiten

`src/batch_nemotron_parse.py` wählt standardmäßig 100 Bilder gleichverteilt und ohne Zurücklegen aus dem oben verlinkten Hugging-Face-Dataset aus. Jedes Bild wird über einen OpenAI-kompatiblen Nebius-Chat-Completions-Endpunkt an Nemotron Parse gesendet und als Text gespeichert. Die Dataset-ID ist nicht pro Seite eindeutig; Dateinamen enthalten deshalb zusätzlich die Position im Batch. Koordinaten- und Klassentags des Parsers werden aus dem Text entfernt; die unveränderte API-Antwort bleibt in `records.jsonl` erhalten.

Zuerst `python -m pip install -r requirements-pipeline.txt` ausführen und die folgenden Werte in einer `.env` im Repository-Stammverzeichnis eintragen. Das Skript lädt diese Datei automatisch; bereits gesetzte Umgebungsvariablen haben Vorrang.

```dotenv
PARSE_MODEL=nvidia/nemotron-3.5-parse
PARSE_API_URL=https://port8000-kh2kceraevwe0k1.tunnel.applications.uk-south2.nebius.cloud/v1/chat/completions
PARSE_API_KEY=
```

`PARSE_MODEL` muss die genaue Kennung des Modells aus `GET /v1/models` des jeweiligen Endpunkts enthalten. Für den oben verlinkten dedizierten Parser wurde `nvidia/nemotron-3.5-parse` bestätigt. Ohne Modellkennung bricht das Skript vor dem Dataset-Download ab.

Ohne `PARSE_API_URL` wird Token Factory mit `NEBIUS_API_KEY` angesprochen. Für einen dedizierten `PARSE_API_URL` wird nur der optionale `PARSE_API_KEY` verwendet. `.env` ist durch `.gitignore` ausgeschlossen; für Nebius-Jobs können Schlüssel über SecretStash als Secret-Umgebungsvariable gesetzt werden.

Windows PowerShell:

```powershell
$env:PARSE_API_URL = "https://port8000-kh2kceraevwe0k1.tunnel.applications.uk-south2.nebius.cloud/v1/chat/completions"
$env:PARSE_MODEL = "nvidia/nemotron-3.5-parse"
python src/batch_nemotron_parse.py --count 100 --seed 42
```

Bash:

```bash
export PARSE_API_URL="https://port8000-kh2kceraevwe0k1.tunnel.applications.uk-south2.nebius.cloud/v1/chat/completions"
export PARSE_MODEL="nvidia/nemotron-3.5-parse"
python src/batch_nemotron_parse.py --count 100 --seed 42
```

Ergebnisse:

```text
.data/nemotron_parse/
├── records.jsonl       Metadaten, OCR-Text und API-Antwort
└── text/
    ├── 001_<id-1>.txt
    ├── 002_<id-2>.txt
    └── ...
```

Das Script schreibt nach jedem Bild einen Datensatz und leert den Ausgabepuffer. Bei einzelnen API-Fehlern wird mit dem nächsten Bild fortgesetzt und der Fehler in `records.jsonl` vermerkt. Die Bilder werden vor dem API-Aufruf als komprimierte JPEG-Data-URI unter ungefähr 180 KB vorbereitet, damit sie inline an die API gesendet werden können.

Optionen:

```bash
python src/batch_nemotron_parse.py --count 100 --seed 42
python src/batch_nemotron_parse.py --count 100 --model "EXAKTE_NEBIUS_MODELL_ID"
python src/batch_nemotron_parse.py --count 100 --api-url "https://DEIN-ENDPUNKT/v1/chat/completions"
python src/batch_nemotron_parse.py --count 100 --output-dir .data/nemotron_parse_run2
```

Den API-Key bitte nicht im Chat senden. Für die lokale Ausführung selbst als Umgebungsvariable setzen; für den Cloud-Job als Secret konfigurieren.

### Wichtiger Hinweis zu Bildern

Die Query-Ausgabe beschreibt die Treffer. Die eigentlichen Bilddaten liegen im Hugging-Face-Dataset und werden von `datasets` lokal gecacht. Für Training oder Bildverarbeitung kann `iter_rows()` aus `src/query_dataset.py` verwendet werden; dort enthält jedes Ergebnis zusätzlich das Bildobjekt.

