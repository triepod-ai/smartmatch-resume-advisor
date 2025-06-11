"""Configuration settings for the Resume Analyzer API."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # OpenAI Configuration
    openai_api_key: str
    model_name: str = "gpt-3.5-turbo"
    embedding_model: str = "text-embedding-ada-002"
    max_tokens: int = 2000
    temperature: float = 0.3
    
    # LangChain Configuration
    langchain_tracing_v2: bool = True
    langchain_api_key: Optional[str] = None
    langchain_project: str = "resume-analyzer"
    
    # Analysis Configuration
    min_match_threshold: float = 0.3
    max_suggestions: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
