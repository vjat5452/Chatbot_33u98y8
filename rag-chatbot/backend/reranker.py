"""Cross-encoder re-ranker for improving retrieval precision."""

from backend.config import settings

_model = None


def _get_model():
    """Lazy-load the cross-encoder model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        print(f"[Reranker] Loading model: {settings.reranker_model}")
        _model = CrossEncoder(settings.reranker_model)
        print("[Reranker] Model loaded.")
    return _model


def rerank(query: str, results: list[dict], top_k: int | None = None) -> list[dict]:
    """Re-score (query, chunk) pairs with the cross-encoder and return the top_k.

    Args:
        query: The user's search query.
        results: List of result dicts, each must have a "text" key.
        top_k: Number of top results to return (defaults to settings.reranker_top_k).

    Returns:
        The top_k results sorted by cross-encoder score (descending),
        filtered to exclude results below the minimum reranker score.
    """
    if not results:
        return results

    if top_k is None:
        top_k = settings.reranker_top_k

    model = _get_model()
    pairs = [(query, r["text"]) for r in results]
    scores = model.predict(pairs)

    for r, score in zip(results, scores):
        r["rerank_score"] = float(score)

    # Filter out results below minimum cross-encoder score (clearly irrelevant)
    min_score = settings.reranker_min_score
    filtered = [r for r in results if r["rerank_score"] >= min_score]

    if not filtered:
        print(f"[Reranker] All {len(results)} results below threshold {min_score} -- query likely irrelevant")
        return []

    dropped = len(results) - len(filtered)
    if dropped > 0:
        print(f"[Reranker] Dropped {dropped}/{len(results)} results below score {min_score}")

    filtered.sort(key=lambda r: -r["rerank_score"])
    return filtered[:top_k]
