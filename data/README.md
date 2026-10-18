# Dataset

This directory does not contain a copy of the Parquet file. The dataset is loaded from Hugging Face on demand:

- Source: `NationalLibraryOfScotland/encyclopaedia_britannica_illustrated`
- License (per dataset card): CC0 1.0
- Split: `train`
- Size: 2,573 page images (about 374 MB of Parquet)
- Columns: `image`, `label` (`not-illustrated` / `illustrated`), `id` (volume id, shared by several pages), `meta` (volume title)

The binary data is deliberately not checked into Git. `src/query_dataset.py` uses the Hugging Face cache and can search in streaming mode without loading the whole dataset into memory. Everything else in `data/` is local and gitignored.
