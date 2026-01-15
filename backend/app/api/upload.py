from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import UploadResponse
from app.services.document_processor import document_processor
from app.services.qdrant_service import qdrant_service
from app.services.redis_cache import redis_cache
import uuid

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document
    - Extracts text from PDF/DOCX/TXT
    - Chunks the text
    - Indexes chunks in Qdrant
    - Returns file_id for querying
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload PDF, DOCX, or TXT files."
            )

        # Read file content
        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Extract text
        print(f" Processing file: {file.filename}")
        text = document_processor.extract_text(file_content, file.filename)

        if not text or len(text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Could not extract sufficient text from document"
            )

        # Chunk text
        chunks = document_processor.chunk_text(text)

        # Index in Qdrant
        chunks_count = qdrant_service.index_document(file_id, file.filename, chunks)

        print(f" Successfully processed {file.filename} - {chunks_count} chunks")

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            chunks_count=chunks_count,
            message=f"Document uploaded and indexed successfully with {chunks_count} chunks"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.delete("/document/{file_id}")
async def delete_document(file_id: str):
    """Delete a document and its cache entries"""
    try:
        # Delete from Qdrant
        qdrant_service.delete_document(file_id)

        # Clear cache
        redis_cache.clear_file_cache(file_id)

        return {"message": f"Document {file_id} deleted successfully"}

    except Exception as e:
        print(f" Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
