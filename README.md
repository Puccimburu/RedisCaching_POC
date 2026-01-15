# Semantic Query Cache POC

A proof-of-concept chatbot demonstrating **dual-tier semantic query caching** with document Q&A.

## Architecture

**Backend (FastAPI):**
- Document upload and chunking (PDF, DOCX, TXT)
- Qdrant vector storage for document embeddings
- Redis Stack with vector search for semantic caching
- LLM integration (OpenAI GPT-4 / Google Gemini)
- Local embeddings (sentence-transformers/all-MiniLM-L6-v2, 384-dim)

**Frontend (React):**
- File upload interface
- Chat interface with real-time response indicators
- Cache hit/miss visual feedback
- Live cache statistics dashboard

## Key Features

✅ **Dual-Tier Caching** - Original query lookup → Normalized query fallback via LLM
✅ **Semantic Matching** - "What is X?" matches "Explain X", "Tell me about X" using cosine similarity (threshold: 0.9)
✅ **Query Normalization** - LLM-powered query standardization catches typos and paraphrases
✅ **Document Isolation** - Separate cache namespaces per file_id (prevents cross-contamination)
✅ **Lightweight Storage** - Caches only query embeddings + responses (no heavy context)
✅ **Fast Vector Search** - Redis Stack with RediSearch index + manual fallback
✅ **Real-time Analytics** - Track hit rate, total queries, and cached entries

## Dual-Tier Cache Strategy

```
User Query
  │
  ▼
[TIER 1] Redis lookup with original query embedding
  │
  ├─ Cache HIT (similarity ≥ 0.9) → Return cached response (~15ms)
  │
  └─ Cache MISS
       │
       ▼
     [TIER 2] Normalize query with LLM → Redis lookup with normalized embedding
       │
       ├─ Cache HIT → Return cached response + cache original query for future
       │
       └─ Cache MISS
            │
            ▼
          Fetch context from Qdrant → Generate LLM response → Cache both forms
```

## Setup

### Prerequisites
- Python 3.13+
- Node.js 18+
- Redis Stack (self-hosted for vector search)
- Qdrant (self-hosted for document storage)

### Services Setup

**Redis Stack (self-hosted):**
```bash
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

**Qdrant (self-hosted):**
```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Create `.env` file (see `.env.example`):
```
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Start backend:
```bash
python -m uvicorn app.main:app --reload
```

Backend will run at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend will run at `http://localhost:3000`

## Usage

1. Upload a document (PDF, DOCX, TXT)
2. Ask questions about the document
3. Watch cache hits in real-time
4. View analytics on cache performance

## Project Structure

```
cache-poc/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── upload.py        # Document upload endpoint
│   │   │   └── query.py         # Query endpoint with caching
│   │   ├── services/
│   │   │   ├── document_processor.py  # Document chunking
│   │   │   ├── qdrant_service.py      # Vector storage
│   │   │   ├── redis_cache.py         # Semantic cache
│   │   │   └── llm_service.py         # LLM integration
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic models
│   │   └── core/
│   │       └── config.py        # Configuration
│   ├── requirements.txt
│   ├── .env.example
│   └── .env (create this)
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js
│   │   ├── index.js
│   │   ├── components/
│   │   │   ├── FileUpload.js
│   │   │   ├── ChatInterface.js
│   │   │   └── CacheStats.js
│   │   └── *.css (component styles)
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## How It Works

### Dual-Tier Cache Lookup Process

**Tier 1: Original Query**
1. User submits query: "What is machine learning?"
2. System generates embedding (384-dim vector)
3. Redis searches cache using RediSearch FT.SEARCH with KNN
4. If match found with similarity ≥ 0.9 → Return cached response

**Tier 2: Normalized Query (on Tier 1 miss)**
1. LLM normalizes query: "What is machine learning?" → "Define machine learning"
2. System generates embedding for normalized query
3. Redis searches again with normalized embedding
4. If match found → Return cached response + cache original query for future hits

**On Cache Miss (both tiers)**
1. Fetch relevant context from Qdrant (top 5 chunks)
2. Send context + query to LLM (OpenAI/Gemini)
3. Cache response with both original and normalized query forms

### Statistics Tracking

The system tracks:
- **Total Queries**: All queries processed
- **Cache Hits**: Queries served from cache (Tier 1 or Tier 2)
- **Cache Misses**: Queries requiring LLM generation
- **Hit Rate**: Percentage of cache hits
- **Cached Queries**: Total unique query-response pairs stored

### Example Scenarios

**Scenario 1: Exact Match (Tier 1 Hit)**
- Query 1: "What is Python?"
- Query 2: "What is Python?" → Cache HIT (~15ms)

**Scenario 2: Paraphrase (Tier 2 Hit)**
- Query 1: "Explain Python programming"
- Query 2: "What is Python?" → Normalized → Cache HIT (~20ms)

**Scenario 3: Typo Handling (Tier 2 Hit)**
- Query 1: "What is machine learning?"
- Query 2: "What is machien lerning?" → Normalized → Cache HIT

**Scenario 4: Document Isolation**
- File A, Query: "What is Python?" → Response A
- File B, Query: "What is Python?" → Response B (different context)
- No cross-contamination between files
