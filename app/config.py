"""
Application configuration with validation and environment management.

This module provides centralized configuration following DRY principles.
All configuration is validated on startup to catch errors early.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database
    database_url: str
    database_url_test: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8080,https://memoryscope.dev,https://www.memoryscope.dev,https://scoped-memory-7c9f9.web.app,https://scoped-memory-7c9f9.firebaseapp.com"
    cors_allow_credentials: bool = True
    cors_allowed_headers: str = "Content-Type,Authorization,X-Request-ID"
    
    # Monitoring (optional)
    sentry_dsn: Optional[str] = None
    environment: str = "development"
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> str:
        """Parse CORS origins - keep as string for storage, parse when needed."""
        if isinstance(v, list):
            return ",".join(v)
        return str(v)
    
    @field_validator("cors_allowed_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v) -> str:
        """Parse CORS headers - keep as string for storage, parse when needed."""
        if isinstance(v, list):
            return ",".join(v)
        return str(v)
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def get_cors_headers(self) -> List[str]:
        """Get CORS headers as list."""
        if isinstance(self.cors_allowed_headers, list):
            return self.cors_allowed_headers
        return [header.strip() for header in self.cors_allowed_headers.split(",") if header.strip()]
    
    def validate_required(self) -> List[str]:
        """
        Validate required settings for production.
        
        Returns:
            List of missing required settings
        """
        errors = []
        
        if not self.database_url:
            errors.append("DATABASE_URL is required")
        return errors

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow reading from environment variables
        extra = "ignore"


# Create settings instance
settings = Settings()

# Validate on import (for production)
if os.getenv("VALIDATE_CONFIG", "false").lower() == "true":
    errors = settings.validate_required()
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

