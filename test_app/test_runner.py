"""
Test runner for comprehensive API testing.
"""
import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from test_app.api_client import MemoryAPIClient
from test_app.openai_client import OpenAIDataGenerator
from test_app.config import config


class TestRunner:
    """Comprehensive test runner for the Memory Scope API."""
    
    def __init__(self, api_client: MemoryAPIClient, data_generator: OpenAIDataGenerator):
        """Initialize test runner."""
        self.api = api_client
        self.generator = data_generator
        self.results = {
            "store": {"success": 0, "failed": 0, "errors": []},
            "read": {"success": 0, "failed": 0, "errors": []},
            "continue": {"success": 0, "failed": 0, "errors": []},
            "revoke": {"success": 0, "failed": 0, "errors": []},
        }
        self.stored_memories: List[Dict[str, Any]] = []
        self.revocation_tokens: List[str] = []
    
    def run_all_tests(self, num_users: int = 5, memories_per_user: int = 20):
        """Run comprehensive test suite."""
        print("=" * 80)
        print("Starting Comprehensive API Test Suite")
        print("=" * 80)
        print(f"Users: {num_users}, Memories per user: {memories_per_user}")
        print()
        
        # Health check
        try:
            health = self.api.health_check()
            print(f"✓ API Health Check: {health.get('status', 'unknown')}")
        except Exception as e:
            print(f"✗ API Health Check failed: {e}")
            return
        
        print()
        
        # Generate test data and store memories
        print("Phase 1: Generating and Storing Memories")
        print("-" * 80)
        self._generate_and_store_memories(num_users, memories_per_user)
        print()
        
        # Test reading memories
        print("Phase 2: Reading Memories")
        print("-" * 80)
        self._test_read_memories()
        print()
        
        # Test continue reading
        print("Phase 3: Continue Reading with Revocation Tokens")
        print("-" * 80)
        self._test_continue_read()
        print()
        
        # Test revoking access
        print("Phase 4: Revoking Memory Access")
        print("-" * 80)
        self._test_revoke()
        print()
        
        # Test that revoked tokens don't work
        print("Phase 5: Verifying Revocation")
        print("-" * 80)
        self._test_revoked_tokens()
        print()
        
        # Print summary
        self._print_summary()
    
    def _generate_and_store_memories(self, num_users: int, memories_per_user: int):
        """Generate realistic memories and store them."""
        domains = ["food", "work", "entertainment", "health", "travel", None]
        sources = ["explicit_user_input", "user_setting"]
        ttl_options = [7, 30, 90, 365]
        
        user_profiles = {}
        for user_idx in range(num_users):
            user_id = f"test_user_{user_idx + 1}"
            
            # Generate a user profile for consistency
            try:
                profile = self.generator.generate_user_profile()
                user_profiles[user_id] = profile
                print(f"Generated profile for {user_id}: {profile[:60]}...")
            except Exception as e:
                print(f"Warning: Could not generate profile for {user_id}: {e}")
                user_profiles[user_id] = "Generic user"
            
            # Generate memories for this user
            for mem_idx in range(memories_per_user):
                scope = random.choice(config.test_scopes)
                domain = random.choice(domains)
                source = random.choice(sources)
                ttl_days = random.choice(ttl_options)
                
                try:
                    # Generate realistic value
                    value_json = self.generator.generate_memory_value(scope, domain)
                    
                    # Store memory
                    result = self.api.store_memory(
                        user_id=user_id,
                        scope=scope,
                        value_json=value_json,
                        domain=domain,
                        source=source,
                        ttl_days=ttl_days
                    )
                    
                    self.stored_memories.append({
                        "user_id": user_id,
                        "scope": scope,
                        "domain": domain,
                        "memory_id": result["id"],
                        "created_at": result["created_at"]
                    })
                    
                    self.results["store"]["success"] += 1
                    
                    if (mem_idx + 1) % 5 == 0:
                        print(f"  {user_id}: Stored {mem_idx + 1}/{memories_per_user} memories...")
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.results["store"]["failed"] += 1
                    error_msg = f"{user_id} ({scope}): {str(e)}"
                    self.results["store"]["errors"].append(error_msg)
                    print(f"  ✗ Failed to store memory: {error_msg}")
        
        print(f"\n✓ Stored {self.results['store']['success']} memories successfully")
        if self.results["store"]["failed"] > 0:
            print(f"✗ Failed to store {self.results['store']['failed']} memories")
    
    def _test_read_memories(self):
        """Test reading memories with various purposes."""
        # Group memories by user and scope
        user_scopes = {}
        for mem in self.stored_memories:
            key = (mem["user_id"], mem["scope"], mem["domain"])
            if key not in user_scopes:
                user_scopes[key] = []
            user_scopes[key].append(mem)
        
        # Test reading for each user/scope combination
        purpose_map = {
            "preferences": ["generate personalized content", "make recommendations"],
            "constraints": ["make recommendations", "schedule tasks"],
            "communication": ["generate personalized content", "send notifications"],
            "accessibility": ["render UI", "generate accessible content"],
            "schedule": ["schedule meetings", "execute tasks"],
            "attention": ["send notifications", "render UI"],
        }
        
        tested = 0
        for (user_id, scope, domain), memories in list(user_scopes.items())[:20]:  # Limit to 20 tests
            if not memories:
                continue
            
            purposes = purpose_map.get(scope, ["generate content"])
            purpose = random.choice(purposes)
            
            try:
                result = self.api.read_memory(
                    user_id=user_id,
                    scope=scope,
                    purpose=purpose,
                    domain=domain
                )
                
                # Store revocation token for later tests
                if result.get("revocation_token"):
                    self.revocation_tokens.append({
                        "token": result["revocation_token"],
                        "user_id": user_id,
                        "scope": scope,
                        "domain": domain
                    })
                
                self.results["read"]["success"] += 1
                tested += 1
                
                if tested % 5 == 0:
                    print(f"  Read {tested} memory sets...")
                
                time.sleep(0.1)
                
            except Exception as e:
                self.results["read"]["failed"] += 1
                error_msg = f"{user_id} ({scope}): {str(e)}"
                self.results["read"]["errors"].append(error_msg)
                print(f"  ✗ Failed to read: {error_msg}")
        
        print(f"\n✓ Read {self.results['read']['success']} memory sets successfully")
        if self.results["read"]["failed"] > 0:
            print(f"✗ Failed to read {self.results['read']['failed']} memory sets")
    
    def _test_continue_read(self):
        """Test continuing to read with revocation tokens."""
        if not self.revocation_tokens:
            print("  No revocation tokens available for continue read test")
            return
        
        # Test continuing with a subset of tokens
        tokens_to_test = self.revocation_tokens[:min(10, len(self.revocation_tokens))]
        
        for token_info in tokens_to_test:
            try:
                result = self.api.continue_read_memory(
                    revocation_token=token_info["token"]
                )
                
                self.results["continue"]["success"] += 1
                time.sleep(0.1)
                
            except Exception as e:
                self.results["continue"]["failed"] += 1
                error_msg = f"Token {token_info['token'][:8]}...: {str(e)}"
                self.results["continue"]["errors"].append(error_msg)
                print(f"  ✗ Failed to continue read: {error_msg}")
        
        print(f"✓ Continued reading {self.results['continue']['success']} times successfully")
        if self.results["continue"]["failed"] > 0:
            print(f"✗ Failed to continue read {self.results['continue']['failed']} times")
    
    def _test_revoke(self):
        """Test revoking memory access."""
        if not self.revocation_tokens:
            print("  No revocation tokens available for revoke test")
            return
        
        # Revoke a subset of tokens
        tokens_to_revoke = self.revocation_tokens[:min(5, len(self.revocation_tokens))]
        
        for token_info in tokens_to_revoke:
            try:
                result = self.api.revoke_memory(
                    revocation_token=token_info["token"]
                )
                
                if result.get("revoked"):
                    self.results["revoke"]["success"] += 1
                else:
                    self.results["revoke"]["failed"] += 1
                    self.results["revoke"]["errors"].append(f"Revoke returned revoked=False")
                
                time.sleep(0.1)
                
            except Exception as e:
                self.results["revoke"]["failed"] += 1
                error_msg = f"Token {token_info['token'][:8]}...: {str(e)}"
                self.results["revoke"]["errors"].append(error_msg)
                print(f"  ✗ Failed to revoke: {error_msg}")
        
        print(f"✓ Revoked {self.results['revoke']['success']} tokens successfully")
        if self.results["revoke"]["failed"] > 0:
            print(f"✗ Failed to revoke {self.results['revoke']['failed']} tokens")
    
    def _test_revoked_tokens(self):
        """Test that revoked tokens no longer work."""
        # Try to continue reading with revoked tokens
        revoked_count = 0
        for token_info in self.revocation_tokens[:5]:  # Only test first 5
            try:
                result = self.api.continue_read_memory(
                    revocation_token=token_info["token"]
                )
                # If we get here, the token wasn't revoked or revocation didn't work
                print(f"  ⚠ Token {token_info['token'][:8]}... still works (may not have been revoked)")
            except Exception as e:
                if "REVOKED" in str(e) or "404" in str(e) or "403" in str(e):
                    revoked_count += 1
                    # This is expected - token was revoked
                else:
                    print(f"  ⚠ Unexpected error for revoked token: {e}")
        
        print(f"✓ Verified {revoked_count} tokens are properly revoked")
    
    def _print_summary(self):
        """Print test summary."""
        print("=" * 80)
        print("Test Summary")
        print("=" * 80)
        
        total_success = sum(r["success"] for r in self.results.values())
        total_failed = sum(r["failed"] for r in self.results.values())
        
        for operation, stats in self.results.items():
            print(f"\n{operation.upper()}:")
            print(f"  Success: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            if stats["errors"]:
                print(f"  Errors ({len(stats['errors'])}):")
                for error in stats["errors"][:5]:  # Show first 5 errors
                    print(f"    - {error}")
                if len(stats["errors"]) > 5:
                    print(f"    ... and {len(stats['errors']) - 5} more")
        
        print(f"\n{'=' * 80}")
        print(f"Total: {total_success} successful, {total_failed} failed")
        print(f"Success Rate: {total_success / (total_success + total_failed) * 100:.1f}%")
        print("=" * 80)

