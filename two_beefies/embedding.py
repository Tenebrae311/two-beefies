"""Validated embeddings: Nemotron NIM or the explicitly configured Qwen fallback."""

import math
import time

import requests

from two_beefies.schema import EMBED_DIM

QWEN_EMBED_MODEL = "Qwen/Qwen3-Embedding-8B"
QWEN_QUERY_INSTRUCTION = "Given a web search query, retrieve relevant encyclopedia passages that answer the query"


def embedding_payload(texts: list[str], model: str, input_type: str) -> dict:
    if input_type not in {"passage", "query"}:
        raise ValueError("Embedding input type must be passage or query")
    if model == QWEN_EMBED_MODEL:
        # Qwen supports native Matryoshka output dimensions. Request 2048 from
        # the service; never pad vectors or silently slice a different dimension.
        inputs = ([f"Instruct: {QWEN_QUERY_INSTRUCTION}\nQuery:{text}" for text in texts]
                  if input_type == "query" else texts)
        return {"model": model, "input": inputs, "dimensions": EMBED_DIM, "encoding_format": "float"}
    return {"model": model, "input": texts, "input_type": input_type,
            "modality": "text", "encoding_format": "float", "truncate": "END"}


def embed_passages(texts: list[str], *, url: str, model: str, api_key: str = "",
                    batch_size: int = 16, timeout: int = 120) -> list[list[float]]:
    return embed_texts(texts, url=url, model=model, api_key=api_key,
                       batch_size=batch_size, timeout=timeout, input_type="passage")


def embed_texts(texts: list[str], *, url: str, model: str, api_key: str = "",
                batch_size: int = 16, timeout: int = 120, input_type: str = "passage") -> list[list[float]]:
    if not url or not model:
        raise ValueError("EMBED_URL and EMBED_MODEL must be configured")
    if batch_size < 1:
        raise ValueError("Embedding batch size must be positive")
    url = url.rstrip("/")
    if not url.endswith("/embeddings"):
        url += "/v1/embeddings" if not url.endswith("/v1") else "/embeddings"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers,
                                         json=embedding_payload(batch, model, input_type), timeout=timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        response.raise_for_status()
        payload = response.json()
        if payload.get("model") and payload["model"] != model:
            raise ValueError("Embedding response model differs from the requested model")
        data = payload["data"]
        if sorted(item["index"] for item in data) != list(range(len(batch))):
            raise ValueError("Embedding response has missing or duplicate passage indices")
        for item in sorted(data, key=lambda item: item["index"]):
            vector = item["embedding"]
            if len(vector) != EMBED_DIM:
                raise ValueError(f"Expected {EMBED_DIM} embedding dimensions, got {len(vector)}")
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
                raise ValueError("Embedding contains invalid numeric values")
            if not any(vector):
                raise ValueError("Embedding is a zero vector")
            vectors.append(vector)
    return vectors
