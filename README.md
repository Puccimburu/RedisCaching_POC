# Semantic Query Cache POC

A proof-of-concept chatbot demonstrating semantic query caching with document Q&A.

## Architecture

**Backend (FastAPI):**
- Document upload and chunking
- Qdrant vector storage for document context
- Redis vector search for semantic query caching
- LLM integration (OpenAI/Gemini)

**Frontend (React):**
- File upload interface
- Chat interface
- Real-time cache hit/miss indicators
- Cache analytics dashboard

## Key Features

✅ **Semantic Query Matching** - "What is X?" matches "Explain X", "Tell me about X", etc.
✅ **Document Isolation** - Each file has separate cache namespace (no cross-contamination)
✅ **Lightweight Storage** - Only query + response cached (no heavy context)
✅ **Fast Lookups** - Redis vector search (~15ms vs 3s LLM calls)

## Cache Strategy

```
User Query → Check Redis (semantic search on query + file_id)
  ├─ Cache HIT (similarity > 0.9) → Return cached response (15ms)
  └─ Cache MISS → Fetch context from Qdrant → Call LLM → Cache result
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

## Testing Cache Performance

The POC includes test scenarios:
1. Exact query repetition
2. Paraphrased queries
3. Typos and case variations
4. Cross-document isolation
5. Cache hit rate analytics
