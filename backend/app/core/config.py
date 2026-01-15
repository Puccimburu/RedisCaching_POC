from pydantic_settings import BaseSettings
from typing import Literal
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from external secrets folder FIRST (like main project)
external_paths = [
    Path(r'C:\Users\PUCCI\Desktop\secrets\env'),
    Path(r'C:\Users\PUCCI\Desktop\secrets\.env'),
]

for path in external_paths:
    if path.exists():
        load_dotenv(path, override=True)
        print(f" Loaded environment variables from: {path}")
        # Check for GEMINI_API_KEY (used in secrets file) and set GOOGLE_API_KEY
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            os.environ["GOOGLE_API_KEY"] = gemini_key  # Set for LangChain
            print(f" GEMINI_API_KEY loaded and set as GOOGLE_API_KEY: {gemini_key[:10]}...")
        else:
            print(" GEMINI_API_KEY not found in environment!")
        break

# Also load local .env (for local overrides)
local_env = Path(__file__).parent.parent.parent / ".env"
if local_env.exists():
    load_dotenv(local_env, override=False)  # Don't override secrets

class Settings(BaseSettings):
    # LLM Configuration
    LLM_PROVIDER: Literal["gemini", "openai"] = "gemini"
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    REDIS_PASSWORD: str = ""

    # Qdrant Configuration
    QDRANT_CLUSTER_URL: str = ""  # Cloud URL like https://xxxxx.qdrant.io
    QDRANT_HOST: str = "localhost"  # Fallback for local
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "cache_poc_documents"

    # Cache Settings
    CACHE_SIMILARITY_THRESHOLD: float = 0.9

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        # Don't use env_file, we load manually above
        case_sensitive = True

settings = Settings()
