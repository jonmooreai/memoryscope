"""
Configuration for the test app.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class TestAppConfig(BaseSettings):
    """Configuration for the test app."""
    
    # API Configuration
    api_base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None  # Can be set via OPENAI_API_KEY env var
    openai_model: str = "gpt-4o-mini"  # Use cheaper model for test data generation
    
    # Test Configuration
    num_test_users: int = 5
    memories_per_user: int = 20
    test_scopes: list[str] = [
        "preferences",
        "constraints", 
        "communication",
        "accessibility",
        "schedule",
        "attention"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global config instance
config = TestAppConfig()

