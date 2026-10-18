"""Validated document embeddings from the same Nemotron model service used for retrieval."""

import math
import time

import requests

from two_beefies.schema import EMBED_DIM


def embed_passages(texts: list[str], *, url: str, model: str, api_key: str = "",
                   batch_size: int = 16, timeout: int = 120) -> list[list[float]]:
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
                # Organizers' model service: input_type is "query" or "document"; unknown
                # fields (modality, truncate, ...) are rejected with 422.
                response = requests.post(url, headers=headers, json={
                    "model": model, "input": batch, "input_type": "document",
                }, timeout=timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        response.raise_for_status()
        data = response.json()["data"]
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
