# two-beefies

Repo for the Nebius Build Week Hackathon in partnership with NVIDIA.

## Enthaltene Daten

Das Projekt bindet das Hugging-Face-Dataset [NationalLibraryOfScotland/encyclopaedia_britannica_illustrated](https://huggingface.co/datasets/NationalLibraryOfScotland/encyclopaedia_britannica_illustrated) ein.

Es handelt sich um 2.573 historische Bilder aus der Encyclopaedia-Britannica-Sammlung der National Library of Scotland. Jede Zeile enthält:

- `image`: Bild
- `label`: `not-illustrated` oder `illustrated`
- `id`: Datensatz-ID
- `meta`: bibliografische Metadaten

Die Parquet-Datei ist ungefähr 374 MB groß und wird deshalb nicht direkt in Git gespeichert. Stattdessen lädt der Query-Code sie bei der ersten Verwendung von Hugging Face und nutzt danach den lokalen Cache. Die Dataset Card nennt CC0 1.0 als Lizenz; bitte die Quelle bei Weiterverwendung trotzdem angeben.

## Projektstruktur

```text
.
├── data/
│   └── README.md              Herkunft, Schema und Speicherentscheidung
├── src/
│   └── query_dataset.py       Laden und Filtern des Datasets
├── .gitignore                 lokale Caches und Datenablagen
├── requirements.txt           Python-Abhängigkeiten
└── README.md                  Projekt- und Nutzungsdokumentation
```

## Einrichtung

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
```

## Content abfragen

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

## Wichtiger Hinweis zu Bildern

Die Query-Ausgabe beschreibt die Treffer. Die eigentlichen Bilddaten liegen im Hugging-Face-Dataset und werden von `datasets` lokal gecacht. Für Training oder Bildverarbeitung kann `iter_rows()` aus `src/query_dataset.py` verwendet werden; dort enthält jedes Ergebnis zusätzlich das Bildobjekt.
