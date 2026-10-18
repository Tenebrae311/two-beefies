"""LanceDB schema contract shared with the data team (part 1).

Team 1 writes these tables; the agent only reads them. Columns marked optional may be
null. `vector` dimension must match the embedding model used for both indexing
(input_type="passage") and querying (input_type="query").
"""

from lancedb.pydantic import LanceModel, Vector

EMBED_DIM = 2048  # llama-nemotron-embed-vl-1b-v2 default; change together with team 1


class BritannicaChunk(LanceModel):
    id: str  # unique row id, cited by the agent as "EB:<id>"
    doc_id: str  # page (or article) id this chunk belongs to
    chunk_index: int
    title: str | None = None  # headword / running head, if known
    section: str | None = None
    text: str  # OCR / Nemotron Parse text (FTS index on this column)
    url: str | None = None  # NLS viewer URL
    image_url: str | None = None  # scan, e.g. https://deriv.nls.uk/dcn30/.../<page_id>.30.jpg
    edition: str | None = None  # e.g. "1st", "7th"
    year: int | None = None
    volume_label: str | None = None  # e.g. "First edition, 1771, Volume 1, A-B"
    page_id: str | None = None
    page_seq: int | None = None
    embed_model: str | None = None
    vector: Vector(EMBED_DIM)


class WikipediaChunk(LanceModel):
    id: str  # cited as "WP:<id>"
    doc_id: str  # Wikipedia page identifier
    chunk_index: int
    title: str
    section: str | None = None
    text: str
    url: str | None = None
    image_url: str | None = None
    wikidata_qid: str | None = None
    revision_id: str | None = None
    date_modified: str | None = None
    embed_model: str | None = None
    vector: Vector(EMBED_DIM)


class Match(LanceModel):
    britannica_doc_id: str
    wikipedia_doc_id: str | None = None  # None when no clear counterpart exists
    rank: int
    vector_score: float | None = None
    rerank_score: float | None = None
    no_clear_match: bool = False
    reason: str | None = None  # why this is (not) a good match
