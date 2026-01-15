from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import time

class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER

        if self.provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
            # Use all-MiniLM-L6-v2 for fast local embeddings
            # 384 dimensions, optimized for speed
            print(" Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print(" SentenceTransformer loaded successfully (MiniLM, 384 dimensions)!")
            self.embeddings = None  # Not using API embeddings
        else:  # openai
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.3
            )
            # Use all-MiniLM-L6-v2 for fast local embeddings
            print(" Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print(" SentenceTransformer loaded successfully (MiniLM, 384 dimensions)!")
            self.embeddings = None

    def generate_response(self, context: str, query: str) -> tuple[str, float]:
        """Generate LLM response with timing"""
        start_time = time.time()

        prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {query}

Instructions:
- Answer based ONLY on the context provided
- If the answer is not in the context, say "I don't have enough information to answer that."
- Be concise and direct
- Do not make up information

Answer:"""

        response = self.llm.invoke(prompt)
        elapsed_ms = (time.time() - start_time) * 1000

        return response.content, elapsed_ms

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a query using local SentenceTransformer"""
        return self.embedding_model.encode(text).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents using local SentenceTransformer"""
        return self.embedding_model.encode(texts).tolist()

    def normalize_query(self, query: str) -> str:
        """
        Normalize query to canonical form using forensic contract analysis framework
        Maps paraphrases to precise legal-technical terminology for better cache hits
        Returns: Normalized/canonical query string
        """
        start_time = time.time()

        prompt = f"""You are a Senior Partner in a Tier 1 Commercial Law Firm performing forensic contract analysis. Normalize user queries to SHORT, precise canonical questions using the 3-Phase Contract Analysis Framework.

CRITICAL: Keep canonical forms CONCISE to ensure stable embeddings and better cache hits.

PHASE 1 - STRUCTURAL INTEGRITY (The "Skeleton"):
- Parties: "What are the parties?"
- Effective Date: "What is the effective date?"
- Expiration: "What is the expiration date?"
- Non-Renewal: "What is the notice of non-renewal deadline?"
- Hierarchy: "Does the MSA or SOW take precedence?"

PHASE 2 - TECHNICAL CLAUSE BREAKDOWN (The "Nerves"):
- Obligations: "What are the obligations?"
- Payment: "What are the payment terms?"
- Late Fees: "What are the late fee provisions?"
- Termination for Cause: "What are the termination for cause provisions?"
- Cure Period: "What is the cure period?"
- Termination for Convenience: "What are the termination for convenience provisions?"
- Liability Limits: "What are the liability limits?"
- Indemnification: "What is the indemnification clause?"
- IP Rights: "What are the IP ownership provisions?"

PHASE 3 - GAPS & RISK ANALYSIS (The "Blindspots"):
- Non-Solicitation: "Is there a non-solicitation clause?"
- Data Breach: "Are there data breach notification requirements?"
- Audit Rights: "Are there audit rights?"
- Insurance: "What are the insurance requirements?"
- GDPR/CCPA: "Are there data protection provisions?"
- Ambiguity: "Are there ambiguous terms?"

NORMALIZATION RULES:
1. Use SHORT, precise canonical forms (NOT verbose descriptions)
2. Map similar intents to the EXACT SAME canonical question
3. Shorter = better for embedding stability
4. Return ONLY the normalized question, nothing else
5. Be absolutely consistent - same legal intent = identical normalized form

Examples:
- "when does this start?" → "What is the effective date?"
- "who are the parties?" → "What are the parties?"
- "who is represented?" → "What are the parties?"
- "what are the parties involved?" → "What are the parties?"
- "how to terminate?" → "What are the termination for cause provisions?"
- "what if we want to exit?" → "What are the termination for convenience provisions?"
- "what are payment terms and late fees?" → "What are the payment terms?"

User query: {query}

Normalized query:"""

        response = self.llm.invoke(prompt)
        elapsed_ms = (time.time() - start_time) * 1000

        normalized = response.content.strip()
        print(f"🔄 Query normalized in {elapsed_ms:.1f}ms: '{query}' → '{normalized}'")

        return normalized


# Singleton instance
llm_service = LLMService()
