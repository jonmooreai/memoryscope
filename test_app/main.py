#!/usr/bin/env python3
"""
Main entry point for the test app.

This script generates realistic test data using OpenAI and thoroughly tests
all API endpoints: store, read, continue read, and revoke.
"""
import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_app.config import config
from test_app.api_client import MemoryAPIClient
from test_app.openai_client import OpenAIDataGenerator
from test_app.test_runner import TestRunner


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the Memory Scope API with OpenAI-generated realistic data"
    )
    parser.add_argument(
        "--api-url",
        default=config.api_base_url,
        help=f"API base URL (default: {config.api_base_url})"
    )
    parser.add_argument(
        "--api-key",
        default=config.api_key,
        help="API key for authentication (or set MEMORY_API_KEY env var)"
    )
    parser.add_argument(
        "--openai-key",
        default=config.openai_api_key,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=config.num_test_users,
        help=f"Number of test users (default: {config.num_test_users})"
    )
    parser.add_argument(
        "--memories",
        type=int,
        default=config.memories_per_user,
        help=f"Number of memories per user (default: {config.memories_per_user})"
    )
    parser.add_argument(
        "--model",
        default=config.openai_model,
        help=f"OpenAI model to use (default: {config.openai_model})"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("MEMORY_API_KEY")
    if not api_key:
        print("Error: API key is required.")
        print("Provide it via --api-key argument or MEMORY_API_KEY environment variable.")
        sys.exit(1)
    
    # Get OpenAI key
    openai_key = args.openai_key or os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OpenAI API key is required.")
        print("Provide it via --openai-key argument or OPENAI_API_KEY environment variable.")
        print("\nPlease provide your OpenAI API key:")
        openai_key = input("OpenAI API Key: ").strip()
        if not openai_key:
            print("Error: OpenAI API key is required.")
            sys.exit(1)
    
    # Initialize clients
    print("Initializing clients...")
    api_client = MemoryAPIClient(args.api_url, api_key)
    data_generator = OpenAIDataGenerator(openai_key)
    data_generator.model = args.model
    
    # Create test runner
    runner = TestRunner(api_client, data_generator)
    
    # Run tests
    try:
        runner.run_all_tests(
            num_users=args.users,
            memories_per_user=args.memories
        )
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        runner._print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

