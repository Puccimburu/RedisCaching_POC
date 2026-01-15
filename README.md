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
- Python 3.10+
- Node.js 18+
- Docker (for Redis Stack & Qdrant)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file:
```
OPENAI_API_KEY=your_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

Start services:
```bash
docker-compose up -d
python -m uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

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
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── upload.py        # Document upload endpoint
│   │   │   └── query.py         # Query endpoint with caching
│   │   ├── services/
│   │   │   ├── qdrant_service.py    # Vector storage
│   │   │   ├── redis_cache.py       # Semantic cache
│   │   │   └── llm_service.py       # LLM integration
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic models
│   │   └── core/
│   │       └── config.py        # Configuration
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── components/
│   │   │   ├── FileUpload.js
│   │   │   ├── ChatInterface.js
│   │   │   └── CacheAnalytics.js
│   │   └── services/
│   │       └── api.js
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Testing Cache Performance

The POC includes test scenarios:
1. Exact query repetition
2. Paraphrased queries
3. Typos and case variations
4. Cross-document isolation
5. Cache hit rate analytics
