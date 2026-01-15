from fastapi import APIRouter, HTTPException
from app.models.schemas import QueryRequest, QueryResponse, CacheStats
from app.services.redis_cache import redis_cache
from app.services.qdrant_service import qdrant_service
from app.services.llm_service import llm_service
from datetime import datetime
import time

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """
    Query a document with dual-tier semantic caching
    - Tier 1: Checks cache with original query
    - Tier 2: If miss, normalizes query with LLM and checks again
    - If cache HIT: returns cached response immediately
    - If cache MISS: fetches context from Qdrant → calls LLM → caches result
    """
    try:
        start_time = time.time()

        query = request.query.strip()
        file_id = request.file_id

        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Step 1: Dual-tier semantic cache lookup
        # Tier 1: Original query → Tier 2: Normalized query (if miss)
        print(f"\n Query: '{query}' | file_id: {file_id}")
        cache_result = redis_cache.lookup(query, file_id)

        if cache_result:
            # Cache HIT
            cached_response, similarity, cached_query = cache_result
            elapsed_ms = (time.time() - start_time) * 1000

            redis_cache.increment_stats(is_hit=True)

            return QueryResponse(
                query=query,
                file_id=file_id,
                response=cached_response,
                cached=True,
                cache_similarity=similarity,
                cached_query=cached_query,
                response_time_ms=elapsed_ms,
                timestamp=datetime.now().isoformat()
            )

        # Cache MISS - fetch from Qdrant + call LLM
        redis_cache.increment_stats(is_hit=False)

        # Get context from Qdrant
        context = qdrant_service.search_context(query, file_id, top_k=5)

        # Generate LLM response
        response, llm_time_ms = llm_service.generate_response(context, query)

        total_time_ms = (time.time() - start_time) * 1000

        # Cache BOTH original and normalized forms for future hits
        # This ensures typos and paraphrases can be caught via normalization
        print(f" Caching original query: '{query}'")
        redis_cache.store(query, file_id, response)

        # Also normalize and cache canonical form
        normalized_query = llm_service.normalize_query(query)
        if normalized_query.lower() != query.lower():
            print(f" Also caching normalized form: '{normalized_query}'")
            redis_cache.store(normalized_query, file_id, response)

        return QueryResponse(
            query=query,
            file_id=file_id,
            response=response,
            cached=False,
            response_time_ms=round(total_time_ms, 2),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        print(f" Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = redis_cache.get_stats()
        return stats

    except Exception as e:
        print(f" Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")
