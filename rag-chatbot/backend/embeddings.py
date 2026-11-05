"""Sentence-transformers wrapper for embedding text."""

from functools import lru_cache
from backend.config import settings

_model = None


def _get_model():
    """Lazy-load the embedding model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[Embeddings] Loading model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        print("[Embeddings] Model loaded.")
    return _model


@lru_cache(maxsize=4096)
def embed_text(text: str) -> list[float]:
    """Embed a single text string. Used for queries. Results are cached."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed a batch of texts. Used for ingestion."""
    model = _get_model()
    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
    return embeddings.tolist()
