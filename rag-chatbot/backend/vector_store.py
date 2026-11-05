"""Qdrant client: create collection, upsert vectors, search."""

import time
from concurrent.futures import ThreadPoolExecutor
from backend.config import settings

_client = None

# Keyword search cache — avoids scrolling all points on every query
_keyword_cache = {"points": None, "ts": 0.0}
_KEYWORD_CACHE_TTL = 600  # 10 minutes (data only changes on ingestion)
_refreshing = False  # prevents concurrent refresh storms
_bg_pool = ThreadPoolExecutor(max_workers=1)


def _get_client():
    """Lazy-init Qdrant client."""
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def _invalidate_keyword_cache():
    """Clear the keyword cache (called after upsert/delete/reset)."""
    _keyword_cache["points"] = None
    _keyword_cache["ts"] = 0.0


def ensure_collection():
    """Create the collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams

    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        try:
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            print(f"[Qdrant] Created collection: {settings.qdrant_collection}")
        except Exception as e:
            # On Windows, stale storage can block creation — try recreate
            print(f"[Qdrant] Create failed ({e}), attempting recreate...")
            try:
                client.recreate_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[Qdrant] Recreated collection: {settings.qdrant_collection}")
            except Exception as e2:
                print(f"[Qdrant] WARNING: Could not create collection: {e2}")
    else:
        print(f"[Qdrant] Collection already exists: {settings.qdrant_collection}")


def reset_collection():
    """Clear all points from the collection."""
    from qdrant_client.models import Filter, FilterSelector

    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection in collections:
        # Delete all points using an empty filter (matches everything)
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=FilterSelector(filter=Filter()),
        )
        _invalidate_keyword_cache()
        print(f"[Qdrant] Cleared all points from: {settings.qdrant_collection}")
    else:
        ensure_collection()


def delete_by_table(table_name: str):
    """Delete all points where table == table_name."""
    from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

    client = _get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="table", match=MatchValue(value=table_name))]
            )
        ),
    )
    _invalidate_keyword_cache()
    print(f"[Qdrant] Deleted all points with table={table_name}")


def delete_by_ids(point_ids: list[int]):
    """Delete specific points by their IDs."""
    from qdrant_client.models import PointIdsList

    if not point_ids:
        return
    client = _get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=PointIdsList(points=point_ids),
    )
    _invalidate_keyword_cache()
    print(f"[Qdrant] Deleted {len(point_ids)} points by ID")


def get_points_count() -> int:
    """Return total number of points in the collection."""
    client = _get_client()
    try:
        info = client.get_collection(settings.qdrant_collection)
        return info.points_count or 0
    except Exception:
        return 0


def points_exist(point_ids: list[int]) -> bool:
    """Check if all given point IDs exist in the collection."""
    if not point_ids:
        return True
    client = _get_client()
    try:
        results = client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=point_ids[:5],  # spot-check first 5
        )
        return len(results) == min(5, len(point_ids))
    except Exception:
        return False


def upsert_chunks(chunk_ids: list[str], vectors: list[list[float]], payloads: list[dict]):
    """Upsert a batch of vectors with payloads into Qdrant."""
    from qdrant_client.models import PointStruct

    client = _get_client()
    points = []
    for cid, vec, payload in zip(chunk_ids, vectors, payloads):
        points.append(PointStruct(
            id=cid,
            vector=vec,
            payload=payload,
        ))

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=batch,
        )

    _invalidate_keyword_cache()
    print(f"[Qdrant] Upserted {len(points)} points")


def search(
    query_vector: list[float],
    top_k: int | None = None,
    table_filter: str | None = None,
    min_score: float | None = None,
) -> list[dict]:
    """Search for similar chunks with score filtering and dedup.

    Returns list of {text, table, chunk_type, score}.
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = _get_client()
    if top_k is None:
        top_k = settings.top_k
    if min_score is None:
        min_score = settings.min_score

    search_filter = None
    if table_filter:
        search_filter = Filter(
            must=[FieldCondition(key="table", match=MatchValue(value=table_filter))]
        )

    try:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
            score_threshold=min_score,
        )
    except Exception as e:
        print(f"[Qdrant] Search error: {e}")
        return []

    # Deduplicate by text content (same chunk ingested multiple times)
    seen_texts = set()
    deduped = []
    for point in results.points:
        text = point.payload.get("text", "")
        if text in seen_texts:
            continue
        seen_texts.add(text)
        deduped.append({
            "text": text,
            "table": point.payload.get("table", ""),
            "chunk_type": point.payload.get("chunk_type", ""),
            "url": point.payload.get("url", ""),
            "score": point.score,
        })

    return deduped


def _refresh_keyword_cache():
    """Scroll all Qdrant points and update the keyword cache. Runs in background."""
    global _refreshing
    try:
        client = _get_client()
        all_points = []
        offset = None
        while True:
            result = client.scroll(
                collection_name=settings.qdrant_collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = result
            all_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset
        _keyword_cache["points"] = all_points
        _keyword_cache["ts"] = time.time()
        print(f"[Qdrant] Keyword cache refreshed: {len(all_points)} points")
    except Exception as e:
        print(f"[Qdrant] Keyword cache refresh failed: {e}")
    finally:
        _refreshing = False


def warm_keyword_cache():
    """Pre-populate the keyword cache at startup so first query doesn't pay the scroll cost."""
    _refresh_keyword_cache()


def keyword_search(keywords: list[str], top_k: int = 10) -> list[dict]:
    """Search chunks by keyword matching (supplements vector search).

    Uses cached points (refreshed every 10 min in background) to avoid
    blocking queries. Serves stale cache while refreshing.
    Returns list of {text, table, chunk_type, url, score} where score = keyword hit ratio.
    """
    import math

    global _refreshing

    # Use cached points; if stale, serve old data and trigger background refresh
    now = time.time()
    if _keyword_cache["points"] is None:
        # First call ever — must block to populate
        _refresh_keyword_cache()
        all_points = _keyword_cache["points"] or []
    elif (now - _keyword_cache["ts"]) >= _KEYWORD_CACHE_TTL:
        # Stale: serve old data, refresh in background
        all_points = _keyword_cache["points"]
        if not _refreshing:
            _refreshing = True
            _bg_pool.submit(_refresh_keyword_cache)
    else:
        all_points = _keyword_cache["points"]

    # Score by keyword hits (with basic stemming + IDF-like weighting)
    keywords_lower = [k.lower() for k in keywords if len(k) > 2]
    if not keywords_lower:
        return []

    # Build keyword roots for partial matching (e.g. "founded" matches "founder")
    keyword_roots = []
    for kw in keywords_lower:
        root = kw
        for suffix in ("ed", "er", "ers", "ing", "ion", "tion", "s"):
            if kw.endswith(suffix) and len(kw) - len(suffix) >= 3:
                root = kw[:-len(suffix)]
                break
        keyword_roots.append(root)

    # First pass: count how many chunks each root appears in (for IDF weighting)
    root_doc_count = {root: 0 for root in keyword_roots}
    total_docs = len(all_points)
    for point in all_points:
        text = point.payload.get("text", "").lower()
        for root in keyword_roots:
            if root in text:
                root_doc_count[root] += 1

    # Weight: rare keywords are more valuable (IDF-like)
    root_weight = {}
    for root in keyword_roots:
        doc_freq = root_doc_count[root]
        if doc_freq == 0:
            root_weight[root] = 0.0
        else:
            # IDF: log(total / doc_freq) — rare terms get higher weight
            root_weight[root] = math.log(max(total_docs, 1) / doc_freq) + 1.0

    total_weight = sum(root_weight.values()) or 1.0

    scored = []
    for point in all_points:
        text = point.payload.get("text", "").lower()
        weighted_hits = sum(root_weight[root] for root in keyword_roots if root in text)
        if weighted_hits > 0:
            scored.append({
                "text": point.payload.get("text", ""),
                "table": point.payload.get("table", ""),
                "chunk_type": point.payload.get("chunk_type", ""),
                "url": point.payload.get("url", ""),
                "score": weighted_hits / total_weight,  # 0.0 to 1.0
                "_weighted_hits": weighted_hits,
            })

    # Sort by weighted hits descending, take top_k
    scored.sort(key=lambda x: -x["_weighted_hits"])
    for item in scored:
        del item["_weighted_hits"]
    return scored[:top_k]


def is_healthy() -> bool:
    """Check if Qdrant is reachable."""
    try:
        client = _get_client()
        client.get_collections()
        return True
    except Exception:
        return False
