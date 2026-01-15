from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    chunks_count: int
    message: str

class QueryRequest(BaseModel):
    query: str
    file_id: str

class QueryResponse(BaseModel):
    query: str
    file_id: str
    response: str
    cached: bool
    cache_similarity: Optional[float] = None
    cached_query: Optional[str] = None
    response_time_ms: float
    timestamp: str

class CacheStats(BaseModel):
    total_queries: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    avg_response_time_cached_ms: float
    avg_response_time_uncached_ms: float

class CacheEntry(BaseModel):
    query: str
    file_id: str
    response: str
    timestamp: str
