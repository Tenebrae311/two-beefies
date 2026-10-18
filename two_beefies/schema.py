"""LanceDB schema contract shared with the data team (part 1).

Team 1 writes these tables; the agent only reads them. Columns marked optional may be
null. `vector` dimension must match the embedding model used for both indexing
(input_type="passage") and querying (input_type="query").
"""

from lancedb.pydantic import LanceModel, Vector

EMBED_DIM = 2048  # llama-nemotron-embed-vl-1b-v2 default; change together with team 1


class BritannicaChunk(LanceModel):
    """One text chunk of a page from the challenge dataset
    NationalLibraryOfScotland/encyclopaedia_britannica_illustrated (split "train").
    The dataset has no page ids, so a page is identified by its row index."""

    id: str  # "<page_index>-<chunk_index>", cited by the agent as "EB:<id>"
    doc_id: str  # str(page_index)
    chunk_index: int
    page_index: int  # row index in the HF dataset
    volume_id: str  # dataset column `id` (NLS volume id, shared by ~13 pages)
    meta: str  # dataset column `meta` (full volume title)
    illustrated: bool  # dataset column `label` == 1
    title: str | None = None  # headwords found on the page, e.g. "NICE, NICHE"
    section: str | None = None
    text: str  # Nemotron Parse text (FTS index on this column)
    url: str | None = None  # dataset viewer link for this row
    image_url: str | None = None  # "/api/page-image/<page_index>" (served from data/pages/)
    edition: str | None = None  # e.g. "4th (1801-1810)"
    year: int | None = None  # first year of that edition
    volume_label: str | None = None  # e.g. "Fourth edition, Volume 15 Part 1, NIC-ORB"
    ocr_model: str | None = None  # parse / vl / tesseract
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
