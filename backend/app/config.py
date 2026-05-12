from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import PostgresDsn
from dotenv import load_dotenv
from typing import Optional   # <-- ADD THIS


class Settings(BaseSettings):

    # App
    app_name: str = "RxDiscrepancy Detection API"
    project_name: str = "RxDetect"
    version: str = "1.0.0"
    debug: bool = True

    # Database
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None

    database_url: PostgresDsn
    async_database_url: str
    
    # JWT
    jwt_secret_key: str = "super_secret_key_change_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = redis_url
    celery_result_backend: str = redis_url
    # Redis
    #redis_host: str = "localhost"
    #redis_port: int = 6379
    #redis_db: int = 0

    # Celery
    #celery_broker_url: str = f"redis://{redis_host}:{redis_port}/{redis_db}"
    #celery_result_backend: str = f"redis://{redis_host}:{redis_port}/{redis_db}"

    # OpenAI
    # LLM / AI Services
    openai_api_key: Optional[str] = None

    openai_vision_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_reasoning_model: str = "gpt-4o"

    # OCR confidence threshold
    ocr_confidence_threshold: float = 0.65

    # AWS
    use_s3: bool = False
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_region: Optional[str] = None

    # Knowledge base (vector DB)
    faiss_index_path: str = "data/faiss_index"

    # Monitoring
    sentry_dsn: Optional[str] = None

    # Storage
    uploads_dir: str = "uploads"
    reports_dir: str = "reports"
    
    
    # Upload settings 
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    
    # Drug APIs
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    openfda_base_url: str = "https://api.fda.gov/drug"
    drugbank_api_key: Optional[str] = None
    eka_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings():
    load_dotenv()
    return Settings()


settings = get_settings()