"""Index only remote title/description metadata; never download the full Wikipedia dump."""

import argparse
import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfApi, HfFileSystem

from two_beefies import config
from two_beefies.wiki_index import INDEX_VERSION, SCHEMA

REPO = "wikimedia/structured-wikipedia"
PROJECTED_COLUMNS = ["identifier", "name", "description", "url", "version.identifier", "main_entity.identifier"]


def remote_shard(path: str, revision: str):
    for attempt in range(4):
        try:
            fs = HfFileSystem(token=False)
            with fs.open(f"datasets/{REPO}/{path}", "rb", revision=revision, block_size=16384) as file:
                parquet = pq.ParquetFile(file)
                rows = parquet.read(columns=PROJECTED_COLUMNS).to_pylist()
            return path, rows
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def build(index_path: Path, workers: int = 8, resume: bool = False) -> dict:
    api = HfApi(token=False)
    if index_path.exists() and not resume:
        raise ValueError("Index exists; use --resume")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(index_path)
    try:
        exists = connection.execute("SELECT name FROM sqlite_master WHERE name='metadata'").fetchone()
        if not exists:
            connection.executescript(SCHEMA)
            revision = api.dataset_info(REPO).sha
            connection.executemany("INSERT INTO metadata VALUES (?,?)", [
                ("version", INDEX_VERSION), ("ready", "0"), ("content_mode", "remote_metadata"),
                ("remote_repo", REPO), ("remote_revision", revision)])
            connection.commit()
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("content_mode") != "remote_metadata":
            raise ValueError("This is not a remote-metadata index")
        revision = metadata["remote_revision"]
        files = sorted(p for p in api.list_repo_files(REPO, repo_type="dataset", revision=revision)
                       if p.startswith("enwiki/data/") and p.endswith(".parquet"))
        if not files:
            raise ValueError("No remote English Wikipedia shards found")
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('expected_shards',?)", (str(len(files)),))
        previous = {r[0] for r in connection.execute("SELECT path FROM shards")}
        connection.execute("UPDATE metadata SET value='0' WHERE key='ready'")
        connection.commit()
        completed = len(previous)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(remote_shard, p, revision) for p in files if p not in previous]
            for future in as_completed(futures):
                path, rows = future.result()
                values = []
                for row_index, row in enumerate(rows):
                    values.append((str(row["identifier"]), row["name"], row["url"], row.get("description") or "",
                                   int((row.get("version") or {}).get("identifier") or 0),
                                   (row.get("main_entity") or {}).get("identifier"),
                                   f"hf://datasets/{REPO}@{revision}/{path}", row_index))
                with connection:
                    connection.executemany("""
                        INSERT INTO articles(doc_id,title,url,description,abstract,body,revision_id,wikidata_qid,
                                             source_file,source_row)
                        VALUES (?,?,?,?,'','',?,?,?,?)
                        ON CONFLICT(doc_id) DO UPDATE SET title=excluded.title,url=excluded.url,
                            description=excluded.description,revision_id=excluded.revision_id,
                            wikidata_qid=excluded.wikidata_qid,source_file=excluded.source_file,source_row=excluded.source_row
                        WHERE excluded.revision_id > articles.revision_id
                    """, values)
                    connection.execute("INSERT INTO shards VALUES (?,?,?)", (path, revision, len(rows)))
                completed += 1
                print(f"Remote metadata {completed}/{len(files)}: {path}, {len(rows)} articles", flush=True)
        snapshot = hashlib.sha256(f"{REPO}@{revision}:title-description-v1".encode()).hexdigest()
        count = connection.execute("SELECT count(*) FROM articles").fetchone()[0]
        if not count:
            raise ValueError("Remote index is empty")
        with connection:
            connection.execute("INSERT OR REPLACE INTO metadata VALUES ('snapshot',?)", (snapshot,))
            connection.execute("UPDATE metadata SET value='1' WHERE key='ready'")
        summary = {"articles": count, "shards": len(files), "revision": revision,
                   "snapshot": snapshot, "content_mode": "remote_metadata"}
        print(json.dumps(summary, indent=2), flush=True)
        return summary
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path(config.WIKI_INDEX_PATH))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("workers must be between 1 and 16")
    build(args.index, args.workers, args.resume)
