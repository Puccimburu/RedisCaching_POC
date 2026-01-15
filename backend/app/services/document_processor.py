from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from docx import Document
from typing import List
import io

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from uploaded file"""
        try:
            if filename.endswith('.pdf'):
                return self._extract_pdf(file_content)
            elif filename.endswith('.docx'):
                return self._extract_docx(file_content)
            elif filename.endswith('.txt'):
                return file_content.decode('utf-8')
            else:
                raise ValueError(f"Unsupported file type: {filename}")

        except Exception as e:
            print(f"  Error extracting text: {e}")
            raise

    def _extract_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)

    def _extract_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)

        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        return "\n\n".join(text_parts)

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        chunks = self.text_splitter.split_text(text)
        print(f" Split text into {len(chunks)} chunks")
        return chunks


# Singleton instance
document_processor = DocumentProcessor()
