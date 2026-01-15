from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.services.llm_service import llm_service
from typing import List, Dict
import uuid

class QdrantService:
    def __init__(self):
        # Connect to Qdrant (matching main project pattern)
        if settings.QDRANT_CLUSTER_URL:
            # Use cloud Qdrant cluster
            self.client = QdrantClient(
                url=settings.QDRANT_CLUSTER_URL,
                api_key=settings.QDRANT_API_KEY
            )
            print(f" Connected to Qdrant Cloud: {settings.QDRANT_CLUSTER_URL}")
        elif settings.QDRANT_API_KEY:
            # Use cloud with QDRANT_HOST
            self.client = QdrantClient(
                url=f"https://{settings.QDRANT_HOST}",
                api_key=settings.QDRANT_API_KEY
            )
            print(f" Connected to Qdrant Cloud: {settings.QDRANT_HOST}")
        else:
            # Use local Qdrant
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
            print(f" Connected to local Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 produces 384-dim vectors
                        distance=Distance.COSINE
                    )
                )
                print(f" Created Qdrant collection: {self.collection_name} (MiniLM 384 dimensions)")
            else:
                print(f" Qdrant collection exists: {self.collection_name}")

            # Create payload index for file_id to enable filtering
            try:
                from qdrant_client.models import PayloadSchemaType
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="file_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                print(f" Created payload index for file_id")
            except Exception as idx_error:
                # Index might already exist, that's fine
                if "already exists" not in str(idx_error).lower():
                    print(f"  Note: {idx_error}")

        except Exception as e:
            print(f"  Error ensuring Qdrant collection: {e}")

    def index_document(self, file_id: str, filename: str, chunks: List[str]) -> int:
        """
        Index document chunks into Qdrant
        Returns: number of chunks indexed
        """
        try:
            # Generate embeddings for all chunks
            embeddings = llm_service.embed_documents(chunks)

            # Create points for Qdrant
            points = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "file_id": file_id,
                        "filename": filename,
                        "text": chunk,
                        "chunk_index": idx
                    }
                )
                points.append(point)

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            print(f" Indexed {len(chunks)} chunks for file_id={file_id}")
            return len(chunks)

        except Exception as e:
            print(f"  Error indexing document: {e}")
            raise

    def search_context(self, query: str, file_id: str, top_k: int = 5) -> str:
        """
        Search for relevant context chunks for a query
        Returns: concatenated context string
        """
        try:
            # Embed the query
            query_embedding = llm_service.embed_query(query)

            # Search in Qdrant with file_id filter (using query method for newer qdrant-client)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                ),
                limit=top_k
            ).points

            if not results:
                return "No relevant context found."

            # Build context from results
            context_parts = []
            for idx, result in enumerate(results, 1):
                text = result.payload.get("text", "")
                filename = result.payload.get("filename", "")
                score = result.score

                context_parts.append(
                    f"[Chunk {idx} - Score: {score:.3f}]\n{text}\n"
                )

            context = "\n---\n".join(context_parts)
            print(f" Retrieved {len(results)} context chunks for query")

            return context

        except Exception as e:
            print(f"  Error searching context: {e}")
            return "Error retrieving context."

    def delete_document(self, file_id: str):
        """Delete all chunks for a specific document"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                )
            )
            print(f"  Deleted all chunks for file_id={file_id}")

        except Exception as e:
            print(f"  Error deleting document: {e}")


# Singleton instance
qdrant_service = QdrantService()
