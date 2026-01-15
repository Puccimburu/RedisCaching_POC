import redis
import json
import struct
import math
from typing import Optional, Tuple
from datetime import datetime
from app.core.config import settings
from app.services.llm_service import llm_service
import time

class RedisSemanticCache:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=False  # Keep as bytes for embedding storage
        )
        self.threshold = settings.CACHE_SIMILARITY_THRESHOLD

        # Initialize index for vector similarity search
        self._ensure_index()

    def _ensure_index(self):
        """Create Redis search index for vector similarity if it doesn't exist"""
        try:
            self.client.execute_command("FT.INFO", "cache_idx")
        except redis.exceptions.ResponseError:
            # Index doesn't exist, create it
            try:
                self.client.execute_command(
                    "FT.CREATE", "cache_idx",
                    "ON", "HASH",
                    "PREFIX", "1", "cache:",
                    "SCHEMA",
                    "file_id", "TAG",
                    "query", "TEXT",
                    "response", "TEXT",
                    "timestamp", "TEXT",
                    "query_embedding", "VECTOR", "FLAT", "6", "TYPE", "FLOAT32", "DIM", "384", "DISTANCE_METRIC", "COSINE"  # all-MiniLM-L6-v2 uses 384 dimensions
                )
                print(" Redis search index created successfully")
            except Exception as e:
                print(f"  Warning: Could not create Redis index: {e}")
                print("   Falling back to simple key-value cache (no semantic search)")

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors without numpy"""
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    def lookup(self, query: str, file_id: str) -> Optional[Tuple[str, float, str]]:
        """
        Dual-tier cache lookup:
        1. Try original query (Tier 1)
        2. If miss, normalize query and try again (Tier 2)
        Returns: (cached_response, similarity_score, original_query) or None
        """
        start_time = time.time()

        # Tier 1: Try original query
        print(f"🔍 [TIER 1] Looking up original query...")
        result = self._lookup_single_query(query, file_id, start_time)

        if result is not None:
            print(f" [TIER 1] Direct cache hit!")
            return result

        # Tier 2: Try normalized query
        print(f" [TIER 2] Cache miss, trying normalized query...")
        normalized_query = llm_service.normalize_query(query)

        # Store mapping of original → normalized for future reference
        print(f" [TIER 2] Searching cache with normalized query...")
        result = self._lookup_single_query(normalized_query, file_id, start_time)

        if result is not None:
            print(f" [TIER 2] Cache hit via normalization!")
            # Cache both original query AND normalized query for future hits
            cached_response, similarity, cached_query = result
            print(f" [TIER 2] Storing original query mapping for future direct hits...")
            self.store(query, file_id, cached_response)
            # Also ensure normalized form is cached (if not already the same)
            if normalized_query.lower() != query.lower():
                print(f" [TIER 2] Ensuring normalized form is cached: '{normalized_query}'")
                self.store(normalized_query, file_id, cached_response)
            return result

        print(f" [TIER 2] No cache match found after normalization")
        return None

    def _lookup_single_query(self, query: str, file_id: str, start_time: float) -> Optional[Tuple[str, float, str]]:
        """
        Look up a single query in cache using RediSearch vector index
        Returns: (cached_response, similarity_score, original_query) or None
        """
        # Embed the query
        embed_start = time.time()
        query_embedding = llm_service.embed_query(query)
        embed_time_ms = (time.time() - embed_start) * 1000
        print(f"⏱  Embedding generation time: {embed_time_ms:.1f}ms")

        # Try RediSearch vector search first (FAST)
        print(f" Attempting RediSearch vector index lookup...")
        try:
            result = self._redisearch_lookup(query_embedding, file_id, start_time)
            if result is not None:
                return result
        except Exception as e:
            print(f"  RediSearch lookup failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("   Falling back to manual search...")

        # Fallback to manual search (SLOW but works without RediSearch)
        print(f"🔄 Using manual search fallback...")
        return self._manual_lookup(query_embedding, file_id, start_time)

    def _redisearch_lookup(self, query_embedding: list[float], file_id: str, start_time: float) -> Optional[Tuple[str, float, str]]:
        """
        Use RediSearch vector index for fast semantic search
        """
        redis_search_start = time.time()

        print(f"   → RediSearch: Converting embedding to bytes ({len(query_embedding)} floats - MiniLM 384-dim)")
        # Convert embedding to bytes for RediSearch
        embedding_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)

        print(f"   → RediSearch: Executing FT.SEARCH with file_id filter: {file_id}")
        # RediSearch KNN query with file_id filter
        # Escape file_id for TAG query - replace hyphens and special chars
        escaped_file_id = file_id.replace("-", "\\-")

        # RediSearch vector KNN syntax: combine TAG filter with KNN vector search
        # Format: (tag_filter)=>[KNN k @vector_field $param AS score_name]
        query = f"(@file_id:{{{escaped_file_id}}})=>[KNN 10 @query_embedding $query_vec AS vector_score]"

        ft_search_start = time.time()
        result = self.client.execute_command(
            "FT.SEARCH", "cache_idx",
            query,
            "RETURN", "3", "query", "response", "query_embedding",
            "SORTBY", "vector_score",  # Sort by KNN score
            "DIALECT", "2",
            "LIMIT", "0", "1",  # Get top 1 match
            "PARAMS", "2", "query_vec", embedding_bytes
        )
        ft_search_time_ms = (time.time() - ft_search_start) * 1000
        print(f"   → RediSearch: Query executed in {ft_search_time_ms:.1f}ms, parsing results...")

        # Parse RediSearch result
        # Result format: [total_count, key1, [field1, value1, field2, value2], key2, ...]
        if not result or result[0] == 0:
            print(f"   → RediSearch: No results found (result count: {result[0] if result else 'None'})")
            return None

        print(f"   → RediSearch: Found {result[0]} result(s)")

        # Get top match
        # result[1] = key, result[2] = [field, value, field, value, ...]
        fields = result[2]

        # Parse fields array
        cached_query = None
        cached_response = None
        cached_embedding_bytes = None

        for i in range(0, len(fields), 2):
            field_name = fields[i].decode('utf-8') if isinstance(fields[i], bytes) else fields[i]
            field_value = fields[i+1]

            if field_name == "query":
                cached_query = field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value
            elif field_name == "response":
                cached_response = field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value
            elif field_name == "query_embedding":
                cached_embedding_bytes = field_value

        if not cached_query or not cached_response or not cached_embedding_bytes:
            return None

        # Calculate similarity manually to verify threshold
        num_floats = len(cached_embedding_bytes) // 4
        cached_embedding = list(struct.unpack(f'{num_floats}f', cached_embedding_bytes))
        similarity = self._cosine_similarity(query_embedding, cached_embedding)

        elapsed_ms = (time.time() - start_time) * 1000

        if similarity >= self.threshold:
            print(f" Cache HIT (RediSearch): similarity={similarity:.3f}, lookup_time={elapsed_ms:.1f}ms")
            print(f"   Original query: {cached_query}")
            print(f"   Method: RediSearch vector index")
            return (cached_response, similarity, cached_query)
        else:
            print(f" Cache MISS (RediSearch): best_similarity={similarity:.3f} (threshold={self.threshold})")
            return None

    def _manual_lookup(self, query_embedding: list[float], file_id: str, start_time: float) -> Optional[Tuple[str, float, str]]:
        """
        Fallback manual search by looping through all keys
        """
        try:
            manual_search_start = time.time()

            # Get all cache entries for this file_id
            pattern = f"cache:{file_id}:*"
            keys = self.client.keys(pattern)
            print(f"   → Manual: Found {len(keys)} keys to search through")

            if not keys:
                return None

            best_match = None
            best_similarity = 0.0
            best_cached_query = ""

            for key in keys:
                cached_data = self.client.hgetall(key)
                if not cached_data:
                    continue

                # Get cached embedding
                cached_embedding_bytes = cached_data.get(b'query_embedding')
                if not cached_embedding_bytes:
                    continue

                # Convert bytes to float array (without numpy)
                num_floats = len(cached_embedding_bytes) // 4
                cached_embedding = list(struct.unpack(f'{num_floats}f', cached_embedding_bytes))

                # Calculate similarity
                similarity = self._cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cached_data.get(b'response').decode('utf-8')
                    best_cached_query = cached_data.get(b'query').decode('utf-8')

            manual_search_time_ms = (time.time() - manual_search_start) * 1000
            elapsed_ms = (time.time() - start_time) * 1000

            if best_similarity >= self.threshold:
                print(f" Cache HIT (Manual): similarity={best_similarity:.3f}, total_time={elapsed_ms:.1f}ms")
                print(f"   → Manual search time: {manual_search_time_ms:.1f}ms (looped through {len(keys)} keys)")
                print(f"   Original query: {best_cached_query}")
                print(f"   Method: Manual loop (fallback)")
                return (best_match, best_similarity, best_cached_query)
            else:
                print(f" Cache MISS: best_similarity={best_similarity:.3f} (threshold={self.threshold})")
                return None

        except Exception as e:
            print(f"  Manual cache lookup error: {e}")
            return None

    def store(self, query: str, file_id: str, response: str):
        """Store query and response in cache with embedding"""
        try:
            # Generate unique key
            timestamp = datetime.now().isoformat()
            key = f"cache:{file_id}:{hash(query + timestamp)}"

            # Embed the query
            query_embedding = llm_service.embed_query(query)
            # Convert to bytes without numpy
            embedding_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)

            # Store in Redis
            self.client.hset(key, mapping={
                "query": query,
                "file_id": file_id,
                "response": response,
                "timestamp": timestamp,
                "query_embedding": embedding_bytes
            })

            # Set expiration (optional - 24 hours)
            self.client.expire(key, 86400)

            print(f" Cached query for file_id={file_id}")

        except Exception as e:
            print(f"  Cache store error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics"""
        try:
            total_keys = len(self.client.keys("cache:*"))

            # Get stats from a separate stats hash
            stats_key = "cache_stats"
            stats = self.client.hgetall(stats_key)

            if not stats:
                return {
                    "total_cached_queries": total_keys,
                    "total_queries": 0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "hit_rate": 0.0
                }

            total_queries = int(stats.get(b'total_queries', 0))
            cache_hits = int(stats.get(b'cache_hits', 0))

            return {
                "total_cached_queries": total_keys,
                "total_queries": total_queries,
                "cache_hits": cache_hits,
                "cache_misses": total_queries - cache_hits,
                "hit_rate": (cache_hits / total_queries * 100) if total_queries > 0 else 0.0
            }

        except Exception as e:
            print(f"  Error getting stats: {e}")
            return {}

    def increment_stats(self, is_hit: bool):
        """Increment cache statistics"""
        try:
            stats_key = "cache_stats"
            self.client.hincrby(stats_key, "total_queries", 1)
            if is_hit:
                self.client.hincrby(stats_key, "cache_hits", 1)
        except Exception as e:
            print(f"  Error incrementing stats: {e}")

    def clear_file_cache(self, file_id: str):
        """Clear all cache entries for a specific file"""
        pattern = f"cache:{file_id}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
            print(f"  Cleared {len(keys)} cache entries for file_id={file_id}")


# Singleton instance
redis_cache = RedisSemanticCache()
