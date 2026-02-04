#!/usr/bin/env python3
"""
Example usage of the test app components.

This demonstrates how to use the API client and data generator separately.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_app.api_client import MemoryAPIClient
from test_app.openai_client import OpenAIDataGenerator


def example_basic_usage():
    """Example of basic usage."""
    # Get credentials
    api_key = os.getenv("MEMORY_API_KEY", "your-api-key-here")
    openai_key = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
    api_url = os.getenv("MEMORY_API_URL", "http://localhost:8000")
    
    # Initialize clients
    api = MemoryAPIClient(api_url, api_key)
    generator = OpenAIDataGenerator(openai_key)
    
    # Generate a realistic memory
    print("Generating realistic preference memory...")
    value_json = generator.generate_memory_value("preferences", domain="food")
    print(f"Generated value: {value_json}")
    
    # Store it
    print("\nStoring memory...")
    result = api.store_memory(
        user_id="example_user",
        scope="preferences",
        value_json=value_json,
        domain="food",
        ttl_days=30
    )
    print(f"Stored memory with ID: {result['id']}")
    
    # Read it back
    print("\nReading memory...")
    read_result = api.read_memory(
        user_id="example_user",
        scope="preferences",
        purpose="generate personalized food recommendations",
        domain="food"
    )
    print(f"Summary: {read_result['summary_text']}")
    print(f"Confidence: {read_result['confidence']}")
    print(f"Revocation token: {read_result['revocation_token'][:20]}...")
    
    # Continue reading
    print("\nContinuing to read...")
    continue_result = api.continue_read_memory(
        revocation_token=read_result['revocation_token']
    )
    print(f"Summary: {continue_result['summary_text']}")
    
    # Revoke access
    print("\nRevoking access...")
    revoke_result = api.revoke_memory(
        revocation_token=read_result['revocation_token']
    )
    print(f"Revoked: {revoke_result['revoked']}")
    print(f"Revoked at: {revoke_result['revoked_at']}")


if __name__ == "__main__":
    example_basic_usage()

