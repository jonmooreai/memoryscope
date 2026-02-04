from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_SCOPES = {"preferences", "constraints", "communication", "accessibility", "schedule", "attention"}
ALLOWED_SOURCES = {"explicit_user_input", "user_setting"}
ALLOWED_PURPOSE_CLASSES = {
    "content_generation",
    "recommendation",
    "scheduling",
    "ui_rendering",
    "notification_delivery",
    "task_execution",
}

# Policy matrix: scope -> allowed purpose_classes
POLICY_MATRIX = {
    "preferences": {"content_generation", "recommendation"},
    "constraints": {"recommendation", "scheduling", "task_execution"},
    "communication": {"content_generation", "notification_delivery", "ui_rendering"},
    "accessibility": {"ui_rendering", "content_generation", "notification_delivery"},
    "schedule": {"scheduling", "task_execution"},
    "attention": {"notification_delivery", "ui_rendering"},
}

# Value shape schemas
VALUE_SHAPES = {
    "kv_map": {"type": "object"},
    "likes_dislikes": {"type": "object", "properties": {"likes": {"type": "array"}, "dislikes": {"type": "array"}}},
    "rules_list": {"type": "array"},
    "schedule_windows": {"type": "array"},
    "boolean_flags": {"type": "object"},
    "attention_settings": {"type": "object"},
}


class MemoryCreateRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user", examples=["user123"])
    scope: str = Field(..., description="Memory scope (preferences, constraints, communication, accessibility, schedule, attention)", examples=["preferences"])
    domain: Optional[str] = Field(None, description="Optional domain/sub-category within the scope", examples=["food", "music", "work"])
    source: str = Field(..., description="Source of the memory (explicit_user_input or user_setting)", examples=["explicit_user_input"])
    ttl_days: int = Field(ge=1, le=365, description="Time-to-live in days (1-365)", examples=[30, 90, 365])
    value_json: Union[Dict[str, Any], List[Any]] = Field(..., description="Memory data as JSON object or array", examples=[
        {"likes": ["coffee", "tea"], "dislikes": ["milk"]},
        {"theme": "dark", "language": "en"},
        ["rule1", "rule2", "rule3"]
    ])
    
    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in ALLOWED_SCOPES:
            raise ValueError(f"scope must be one of {ALLOWED_SCOPES}")
        return v
    
    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ALLOWED_SOURCES:
            raise ValueError(f"source must be one of {ALLOWED_SOURCES}")
        return v
    
    @model_validator(mode="after")
    def validate_value_shape(self) -> "MemoryCreateRequest":
        value_json = self.value_json
        shape = self._detect_shape(value_json)
        if shape is None:
            raise ValueError("value_json does not match any allowed shape")
        return self
    
    @staticmethod
    def _detect_shape(value_json: Union[Dict[str, Any], List[Any]]) -> Optional[str]:
        if isinstance(value_json, dict):
            if "likes" in value_json or "dislikes" in value_json:
                return "likes_dislikes"
            if all(isinstance(v, bool) for v in value_json.values()):
                return "boolean_flags"
            if "windows" in value_json or "time_slots" in value_json:
                return "schedule_windows"
            if "focus_mode" in value_json or "do_not_disturb" in value_json:
                return "attention_settings"
            return "kv_map"
        elif isinstance(value_json, list):
            if len(value_json) > 0 and all(isinstance(item, str) for item in value_json):
                return "rules_list"
            if len(value_json) > 0 and all(
                isinstance(item, dict) and ("start" in item or "end" in item or "day" in item)
                for item in value_json
            ):
                return "schedule_windows"
        return None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user123",
                    "scope": "preferences",
                    "domain": "food",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {
                        "likes": ["pizza", "sushi"],
                        "dislikes": ["broccoli"]
                    }
                },
                {
                    "user_id": "user123",
                    "scope": "constraints",
                    "source": "explicit_user_input",
                    "ttl_days": 90,
                    "value_json": {
                        "max_budget": 1000,
                        "preferred_vendors": ["vendor1", "vendor2"]
                    }
                }
            ]
        }
    }


class MemoryCreateResponse(BaseModel):
    id: UUID = Field(..., description="Unique memory identifier", examples=["550e8400-e29b-41d4-a716-446655440000"])
    user_id: str = Field(..., description="User identifier", examples=["user123"])
    scope: str = Field(..., description="Memory scope", examples=["preferences"])
    domain: Optional[str] = Field(None, description="Memory domain", examples=["food"])
    created_at: datetime = Field(..., description="Creation timestamp", examples=["2024-01-01T00:00:00Z"])
    expires_at: datetime = Field(..., description="Expiration timestamp", examples=["2024-01-31T00:00:00Z"])
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "user123",
                    "scope": "preferences",
                    "domain": "food",
                    "created_at": "2024-01-01T00:00:00Z",
                    "expires_at": "2024-01-31T00:00:00Z"
                }
            ]
        }
    }


class MemoryReadRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user", examples=["user123"])
    scope: str = Field(..., description="Memory scope to read", examples=["preferences"])
    domain: Optional[str] = Field(None, description="Optional domain filter", examples=["food"])
    purpose: str = Field(..., description="Purpose for reading (used for policy enforcement)", examples=["generate personalized content", "make recommendations"])
    max_age_days: Optional[int] = Field(default=None, ge=1, description="Maximum age of memories to include (in days)", examples=[30, 90])
    
    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in ALLOWED_SCOPES:
            raise ValueError(f"scope must be one of {ALLOWED_SCOPES}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user123",
                    "scope": "preferences",
                    "domain": "food",
                    "purpose": "generate personalized food recommendations",
                    "max_age_days": 30
                }
            ]
        }
    }


class MemoryReadResponse(BaseModel):
    summary_text: str = Field(max_length=240, description="Human-readable summary of memories", examples=["Likes: 2, Dislikes: 1, Settings: 0"])
    summary_struct: Dict[str, Any] = Field(max_length=2048, description="Structured summary data", examples=[{"likes": ["pizza", "sushi"], "dislikes": ["broccoli"]}])
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)", examples=[0.85, 0.9])
    revocation_token: str = Field(..., description="Token to revoke this read grant", examples=["550e8400-e29b-41d4-a716-446655440000"])
    expires_at: datetime = Field(..., description="When the revocation token expires", examples=["2024-01-02T00:00:00Z"])
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary_text": "Likes: 2, Dislikes: 1, Settings: 0",
                    "summary_struct": {
                        "likes": ["pizza", "sushi"],
                        "dislikes": ["broccoli"],
                        "settings": {}
                    },
                    "confidence": 0.85,
                    "revocation_token": "550e8400-e29b-41d4-a716-446655440000",
                    "expires_at": "2024-01-02T00:00:00Z"
                }
            ]
        }
    }


class MemoryReadContinueRequest(BaseModel):
    revocation_token: str = Field(..., description="Revocation token from previous read", examples=["550e8400-e29b-41d4-a716-446655440000"])
    max_age_days: Optional[int] = Field(default=None, ge=1, description="Maximum age of memories to include (in days)", examples=[30])
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "revocation_token": "550e8400-e29b-41d4-a716-446655440000",
                    "max_age_days": 30
                }
            ]
        }
    }


class MemoryRevokeRequest(BaseModel):
    revocation_token: str = Field(..., description="Revocation token to revoke", examples=["550e8400-e29b-41d4-a716-446655440000"])
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "revocation_token": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    }


class MemoryRevokeResponse(BaseModel):
    revoked: bool = Field(..., description="Whether the revocation was successful", examples=[True])
    revoked_at: datetime = Field(..., description="Timestamp of revocation", examples=["2024-01-01T12:00:00Z"])
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "revoked": True,
                    "revoked_at": "2024-01-01T12:00:00Z"
                }
            ]
        }
    }


# Error response schemas for OpenAPI
class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code", examples=["VALIDATION_ERROR", "AUTHENTICATION_ERROR"])
    message: str = Field(..., description="Human-readable error message", examples=["Request validation failed"])
    request_id: str = Field(..., description="Request ID for tracking", examples=["550e8400-e29b-41d4-a716-446655440000"])
    timestamp: str = Field(..., description="ISO8601 timestamp", examples=["2024-01-01T00:00:00Z"])
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    hint: Optional[str] = Field(None, description="Recovery hint", examples=["Check the request format and required fields"])


class ErrorResponse(BaseModel):
    error: ErrorDetail
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "details": {
                            "fields": [
                                {
                                    "field": "scope",
                                    "message": "scope must be one of {'preferences', 'constraints', ...}",
                                    "type": "value_error"
                                }
                            ]
                        },
                        "hint": "Check the request format and required fields"
                    }
                }
            ]
        }
    }
