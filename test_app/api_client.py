"""
API client for interacting with the Memory Scope API.
"""
import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from test_app.config import config


class MemoryAPIClient:
    """Client for interacting with the Memory Scope API."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize API client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def store_memory(
        self,
        user_id: str,
        scope: str,
        value_json: Union[Dict[str, Any], List[Any]],
        domain: Optional[str] = None,
        source: str = "explicit_user_input",
        ttl_days: int = 30
    ) -> Dict[str, Any]:
        """
        Store a memory.
        
        Returns:
            Response data with memory ID, user_id, scope, created_at, expires_at
        """
        url = f"{self.base_url}/memory"
        payload = {
            "user_id": user_id,
            "scope": scope,
            "value_json": value_json,
            "source": source,
            "ttl_days": ttl_days
        }
        if domain:
            payload["domain"] = domain
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def read_memory(
        self,
        user_id: str,
        scope: str,
        purpose: str,
        domain: Optional[str] = None,
        max_age_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Read memories with policy enforcement.
        
        Returns:
            Response data with summary_text, summary_struct, confidence, revocation_token, expires_at
        """
        url = f"{self.base_url}/memory/read"
        payload = {
            "user_id": user_id,
            "scope": scope,
            "purpose": purpose
        }
        if domain:
            payload["domain"] = domain
        if max_age_days:
            payload["max_age_days"] = max_age_days
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def continue_read_memory(
        self,
        revocation_token: str,
        max_age_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Continue reading memories using a revocation token.
        
        Returns:
            Response data with summary_text, summary_struct, confidence, revocation_token, expires_at
        """
        url = f"{self.base_url}/memory/read/continue"
        payload = {
            "revocation_token": revocation_token
        }
        if max_age_days:
            payload["max_age_days"] = max_age_days
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def revoke_memory(self, revocation_token: str) -> Dict[str, Any]:
        """
        Revoke memory access using a revocation token.
        
        Returns:
            Response data with revoked (bool) and revoked_at (datetime)
        """
        url = f"{self.base_url}/memory/revoke"
        payload = {
            "revocation_token": revocation_token
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        url = f"{self.base_url}/healthz"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

