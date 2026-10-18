# Dataset

Dieses Verzeichnis enthält keine Kopie der Parquet-Datei. Das Dataset wird bei Bedarf von Hugging Face geladen:

- Quelle: `NationalLibraryOfScotland/encyclopaedia_britannica_illustrated`
- Lizenz laut Dataset Card: CC0 1.0
- Split: `train`
- Umfang: 2.573 Bilder
- Spalten: `image`, `label`, `id`, `meta`
- Größe der Parquet-Datei: ca. 374 MB

Die Binärdaten werden absichtlich nicht in Git eingecheckt. `src/query_dataset.py` nutzt den Hugging-Face-Cache und kann im Streaming-Modus suchen, ohne das gesamte Dataset in den Arbeitsspeicher zu laden.
