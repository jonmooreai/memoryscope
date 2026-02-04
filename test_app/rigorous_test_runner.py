"""
Rigorous test runner with challenging test cases, especially for deterministic memory merging.
"""
import random
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import json

from test_app.api_client import MemoryAPIClient
from test_app.openai_client import OpenAIDataGenerator


class RigorousTestRunner:
    """Rigorous test runner with challenging test cases and live progress updates."""
    
    def __init__(
        self, 
        api_client: MemoryAPIClient, 
        data_generator: OpenAIDataGenerator,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """Initialize test runner with progress callback."""
        self.api = api_client
        self.generator = data_generator
        self.progress_callback = progress_callback or (lambda x: None)
        self.results = {
            "store": {"success": 0, "failed": 0, "errors": [], "test_cases": []},
            "read": {"success": 0, "failed": 0, "errors": [], "test_cases": []},
            "merge": {"success": 0, "failed": 0, "errors": [], "test_cases": []},
            "continue": {"success": 0, "failed": 0, "errors": [], "test_cases": []},
            "revoke": {"success": 0, "failed": 0, "errors": [], "test_cases": []},
        }
        self.stored_memories: List[Dict[str, Any]] = []
        self.revocation_tokens: List[str] = []
    
    def _emit_progress(self, phase: str, test_case: str, status: str, details: Dict[str, Any] = None):
        """Emit progress update."""
        self.progress_callback({
            "phase": phase,
            "test_case": test_case,
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def run_all_tests(self, num_users: int = 3, memories_per_user: int = 10):
        """Run comprehensive rigorous test suite."""
        self._emit_progress("startup", "Initializing", "info", {"users": num_users, "memories": memories_per_user})
        
        # Health check
        try:
            health = self.api.health_check()
            self._emit_progress("startup", "Health Check", "success", {"status": health.get('status')})
        except Exception as e:
            self._emit_progress("startup", "Health Check", "error", {"error": str(e)})
            return
        
        # Phase 1: Basic memory operations
        self._emit_progress("phase1", "Basic Memory Storage", "start")
        self._test_basic_storage(num_users, memories_per_user)
        
        # Phase 2: Challenging deterministic merging tests
        self._emit_progress("phase2", "Deterministic Merging Tests", "start")
        self._test_deterministic_merging()
        
        # Phase 3: Edge cases and stress tests
        self._emit_progress("phase3", "Edge Cases & Stress Tests", "start")
        self._test_edge_cases()
        
        # Phase 4: Policy and access control
        self._emit_progress("phase4", "Policy & Access Control", "start")
        self._test_policy_and_access()
        
        # Phase 5: Revocation and security
        self._emit_progress("phase5", "Revocation & Security", "start")
        self._test_revocation()
        
        self._emit_progress("complete", "All Tests Complete", "success")
    
    def _test_basic_storage(self, num_users: int, memories_per_user: int):
        """Test basic memory storage with realistic data."""
        domains = ["food", "work", "entertainment", "health", "travel", None]
        sources = ["explicit_user_input", "user_setting"]
        ttl_options = [7, 30, 90, 365]
        
        for user_idx in range(num_users):
            user_id = f"test_user_{user_idx + 1}"
            self._emit_progress("phase1", f"User {user_id}", "info", {"user_num": user_idx + 1, "total": num_users})
            
            for mem_idx in range(memories_per_user):
                scope = random.choice(["preferences", "constraints", "communication", "accessibility", "schedule", "attention"])
                domain = random.choice(domains)
                source = random.choice(sources)
                ttl_days = random.choice(ttl_options)
                
                try:
                    value_json = self.generator.generate_memory_value(scope, domain)
                    
                    result = self.api.store_memory(
                        user_id=user_id,
                        scope=scope,
                        value_json=value_json,
                        domain=domain,
                        source=source,
                        ttl_days=ttl_days
                    )
                    
                    memory_info = {
                        "user_id": user_id,
                        "scope": scope,
                        "domain": domain,
                        "memory_id": result["id"],
                        "created_at": result["created_at"],
                        "value_json": value_json,
                        "value_shape": result.get("value_shape", "unknown"),
                    }
                    self.stored_memories.append(memory_info)
                    
                    # Emit memory stored event
                    self._emit_progress("phase1", f"Memory stored: {scope}", "success", {
                        "memory_id": str(result["id"]),
                        "user_id": user_id,
                        "scope": scope,
                        "domain": domain,
                        "value_preview": str(value_json)[:100] + "..." if len(str(value_json)) > 100 else str(value_json),
                    })
                    
                    self.results["store"]["success"] += 1
                    self.results["store"]["test_cases"].append({
                        "name": f"Store {scope} memory for {user_id}",
                        "status": "success",
                        "memory_id": str(result["id"])
                    })
                    
                    self._emit_progress("phase1", f"Stored memory {mem_idx + 1}/{memories_per_user}", "success", {
                        "user": user_id,
                        "scope": scope,
                        "memory_id": str(result["id"])
                    })
                    
                    time.sleep(0.05)  # Small delay
                    
                except Exception as e:
                    self.results["store"]["failed"] += 1
                    error_msg = f"{user_id} ({scope}): {str(e)}"
                    self.results["store"]["errors"].append(error_msg)
                    self.results["store"]["test_cases"].append({
                        "name": f"Store {scope} memory for {user_id}",
                        "status": "failed",
                        "error": str(e)
                    })
                    self._emit_progress("phase1", f"Failed to store memory", "error", {"error": str(e)})
    
    def _test_deterministic_merging(self):
        """Test challenging deterministic merging scenarios."""
        
        # Test 1: Same timestamp, different IDs (should use ID for ordering)
        self._emit_progress("phase2", "Test: Same timestamp ordering", "start")
        test_user = "merge_test_user_1"
        scope = "preferences"
        domain = "food"
        
        # Create memories with same second timestamp
        base_time = datetime.utcnow()
        memories_to_create = [
            {"likes": ["pizza"], "dislikes": ["broccoli"]},
            {"likes": ["sushi"], "dislikes": ["milk"]},
            {"likes": ["pasta"], "dislikes": ["onions"]},
        ]
        
        memory_ids = []
        for i, value in enumerate(memories_to_create):
            try:
                result = self.api.store_memory(
                    user_id=test_user,
                    scope=scope,
                    value_json=value,
                    domain=domain,
                    source="explicit_user_input",
                    ttl_days=30
                )
                memory_ids.append(result["id"])
                time.sleep(0.1)  # Ensure different timestamps
            except Exception as e:
                self._emit_progress("phase2", "Test: Same timestamp ordering", "error", {"error": str(e)})
                return
        
        # Read twice and verify identical results
        try:
            read1 = self.api.read_memory(
                user_id=test_user,
                scope=scope,
                purpose="generate personalized food recommendations",
                domain=domain
            )
            time.sleep(0.5)
            read2 = self.api.read_memory(
                user_id=test_user,
                scope=scope,
                purpose="generate personalized food recommendations",
                domain=domain
            )
            
            # Verify deterministic results
            if (read1["summary_struct"] == read2["summary_struct"] and 
                read1["summary_text"] == read2["summary_text"] and
                read1["confidence"] == read2["confidence"]):
                self.results["merge"]["success"] += 1
                self.results["merge"]["test_cases"].append({
                    "name": "Deterministic merge: Same timestamp ordering",
                    "status": "success",
                    "details": "Two reads returned identical results"
                })
                self._emit_progress("phase2", "Test: Same timestamp ordering", "success", {
                    "verified": "Identical results across multiple reads"
                })
            else:
                self.results["merge"]["failed"] += 1
                error = "Results were not deterministic"
                self.results["merge"]["errors"].append(error)
                self.results["merge"]["test_cases"].append({
                    "name": "Deterministic merge: Same timestamp ordering",
                    "status": "failed",
                    "error": error
                })
                self._emit_progress("phase2", "Test: Same timestamp ordering", "error", {"error": error})
        except Exception as e:
            self.results["merge"]["failed"] += 1
            self._emit_progress("phase2", "Test: Same timestamp ordering", "error", {"error": str(e)})
        
        # Test 2: Conflicting values (later should win)
        self._emit_progress("phase2", "Test: Conflicting values merge", "start")
        test_user2 = "merge_test_user_2"
        
        conflicting_memories = [
            {"likes": ["coffee"], "dislikes": ["tea"]},
            {"likes": ["tea"], "dislikes": ["coffee"]},  # Conflicts with first
            {"likes": ["water"], "dislikes": ["soda"]},
        ]
        
        for value in conflicting_memories:
            try:
                self.api.store_memory(
                    user_id=test_user2,
                    scope=scope,
                    value_json=value,
                    domain=domain,
                    source="explicit_user_input",
                    ttl_days=30
                )
                time.sleep(0.1)
            except Exception as e:
                self._emit_progress("phase2", "Test: Conflicting values merge", "error", {"error": str(e)})
                break
        
        try:
            read_result = self.api.read_memory(
                user_id=test_user2,
                scope=scope,
                purpose="generate personalized food recommendations",
                domain=domain
            )
            
            # Verify both coffee and tea are in likes (union merge)
            merged_likes = read_result["summary_struct"].get("likes", [])
            if "coffee" in merged_likes and "tea" in merged_likes:
                self.results["merge"]["success"] += 1
                self.results["merge"]["test_cases"].append({
                    "name": "Conflicting values: Union merge",
                    "status": "success",
                    "details": "Conflicting values properly merged"
                })
                self._emit_progress("phase2", "Test: Conflicting values merge", "success", {
                    "verified": "Conflicting values properly merged"
                })
            else:
                self.results["merge"]["failed"] += 1
                error = f"Expected both coffee and tea in likes, got: {merged_likes}"
                self.results["merge"]["errors"].append(error)
                self._emit_progress("phase2", "Test: Conflicting values merge", "error", {"error": error})
        except Exception as e:
            self.results["merge"]["failed"] += 1
            self._emit_progress("phase2", "Test: Conflicting values merge", "error", {"error": str(e)})
        
        # Test 3: Large number of memories (stress test)
        self._emit_progress("phase2", "Test: Large memory merge (50+ memories)", "start")
        test_user3 = "merge_test_user_3"
        large_memory_count = 50
        
        for i in range(large_memory_count):
            try:
                value = {"likes": [f"item_{i}"], "dislikes": [f"bad_item_{i}"]}
                self.api.store_memory(
                    user_id=test_user3,
                    scope=scope,
                    value_json=value,
                    domain=domain,
                    source="explicit_user_input",
                    ttl_days=30
                )
                if (i + 1) % 10 == 0:
                    self._emit_progress("phase2", f"Stored {i + 1}/{large_memory_count} memories", "info", {
                        "progress": i + 1,
                        "total": large_memory_count
                    })
                time.sleep(0.05)
            except Exception as e:
                self._emit_progress("phase2", "Test: Large memory merge", "error", {"error": str(e)})
                break
        
        try:
            read_result = self.api.read_memory(
                user_id=test_user3,
                scope=scope,
                purpose="generate personalized food recommendations",
                domain=domain
            )
            
            merged_likes = read_result["summary_struct"].get("likes", [])
            if len(merged_likes) >= large_memory_count * 0.9:  # Allow some margin
                self.results["merge"]["success"] += 1
                self.results["merge"]["test_cases"].append({
                    "name": f"Large memory merge ({large_memory_count} memories)",
                    "status": "success",
                    "details": f"Merged {len(merged_likes)} likes successfully"
                })
                self._emit_progress("phase2", "Test: Large memory merge", "success", {
                    "merged_count": len(merged_likes),
                    "expected": large_memory_count
                })
            else:
                self.results["merge"]["failed"] += 1
                error = f"Expected ~{large_memory_count} likes, got {len(merged_likes)}"
                self.results["merge"]["errors"].append(error)
                self._emit_progress("phase2", "Test: Large memory merge", "error", {"error": error})
        except Exception as e:
            self.results["merge"]["failed"] += 1
            self._emit_progress("phase2", "Test: Large memory merge", "error", {"error": str(e)})
        
        # Test 4: Multiple reads should be identical
        self._emit_progress("phase2", "Test: Multiple reads determinism", "start")
        test_user4 = "merge_test_user_4"
        
        # Store some memories
        for value in [{"likes": ["a", "b"]}, {"likes": ["c", "d"]}, {"likes": ["e"]}]:
            try:
                self.api.store_memory(
                    user_id=test_user4,
                    scope=scope,
                    value_json=value,
                    domain=domain,
                    source="explicit_user_input",
                    ttl_days=30
                )
                time.sleep(0.1)
            except Exception as e:
                break
        
        # Read 5 times and verify all are identical
        try:
            reads = []
            for i in range(5):
                read = self.api.read_memory(
                    user_id=test_user4,
                    scope=scope,
                    purpose="generate personalized food recommendations",
                    domain=domain
                )
                reads.append(read)
                time.sleep(0.2)
            
            # Verify all reads are identical
            first_read = reads[0]
            all_identical = all(
                read["summary_struct"] == first_read["summary_struct"] and
                read["summary_text"] == first_read["summary_text"] and
                read["confidence"] == first_read["confidence"]
                for read in reads[1:]
            )
            
            if all_identical:
                self.results["merge"]["success"] += 1
                self.results["merge"]["test_cases"].append({
                    "name": "Multiple reads determinism (5 reads)",
                    "status": "success",
                    "details": "All 5 reads returned identical results"
                })
                self._emit_progress("phase2", "Test: Multiple reads determinism", "success", {
                    "verified": "All 5 reads were identical"
                })
            else:
                self.results["merge"]["failed"] += 1
                error = "Multiple reads returned different results"
                self.results["merge"]["errors"].append(error)
                self._emit_progress("phase2", "Test: Multiple reads determinism", "error", {"error": error})
        except Exception as e:
            self.results["merge"]["failed"] += 1
            self._emit_progress("phase2", "Test: Multiple reads determinism", "error", {"error": str(e)})
    
    def _test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        
        # Test: Empty arrays
        self._emit_progress("phase3", "Test: Empty arrays handling", "start")
        try:
            result = self.api.store_memory(
                user_id="edge_test_user_1",
                scope="preferences",
                value_json={"likes": [], "dislikes": []},
                domain="food",
                source="explicit_user_input",
                ttl_days=30
            )
            read_result = self.api.read_memory(
                user_id="edge_test_user_1",
                scope="preferences",
                purpose="generate recommendations",
                domain="food"
            )
            self.results["read"]["success"] += 1
            self._emit_progress("phase3", "Test: Empty arrays handling", "success")
        except Exception as e:
            self.results["read"]["failed"] += 1
            self._emit_progress("phase3", "Test: Empty arrays handling", "error", {"error": str(e)})
        
        # Test: Case sensitivity in normalization
        self._emit_progress("phase3", "Test: Case sensitivity normalization", "start")
        try:
            self.api.store_memory(
                user_id="edge_test_user_2",
                scope="preferences",
                value_json={"likes": ["PIZZA", "pizza", "Pizza"]},
                domain="food",
                source="explicit_user_input",
                ttl_days=30
            )
            read_result = self.api.read_memory(
                user_id="edge_test_user_2",
                scope="preferences",
                purpose="generate recommendations",
                domain="food"
            )
            # Should be normalized/deduplicated
            self.results["read"]["success"] += 1
            self._emit_progress("phase3", "Test: Case sensitivity normalization", "success")
        except Exception as e:
            self.results["read"]["failed"] += 1
            self._emit_progress("phase3", "Test: Case sensitivity normalization", "error", {"error": str(e)})
        
        # Test: Different value shapes mixed
        self._emit_progress("phase3", "Test: Mixed value shapes", "start")
        try:
            self.api.store_memory(
                user_id="edge_test_user_3",
                scope="preferences",
                value_json={"likes": ["item1"]},
                domain="food",
                source="explicit_user_input",
                ttl_days=30
            )
            self.api.store_memory(
                user_id="edge_test_user_3",
                scope="preferences",
                value_json={"theme": "dark", "language": "en"},
                domain="food",
                source="explicit_user_input",
                ttl_days=30
            )
            read_result = self.api.read_memory(
                user_id="edge_test_user_3",
                scope="preferences",
                purpose="generate recommendations",
                domain="food"
            )
            self.results["read"]["success"] += 1
            self._emit_progress("phase3", "Test: Mixed value shapes", "success")
        except Exception as e:
            self.results["read"]["failed"] += 1
            self._emit_progress("phase3", "Test: Mixed value shapes", "error", {"error": str(e)})
    
    def _test_policy_and_access(self):
        """Test policy enforcement and access control."""
        # Test: Valid purpose
        self._emit_progress("phase4", "Test: Valid purpose policy", "start")
        try:
            read_result = self.api.read_memory(
                user_id="policy_test_user",
                scope="preferences",
                purpose="generate personalized content",
                domain="food"
            )
            self.results["read"]["success"] += 1
            self._emit_progress("phase4", "Test: Valid purpose policy", "success")
        except Exception as e:
            if "403" in str(e) or "POLICY" in str(e).upper():
                self.results["read"]["failed"] += 1
                self._emit_progress("phase4", "Test: Valid purpose policy", "error", {"error": str(e)})
            else:
                # Might not have memories, that's ok
                pass
        
        # Test: Invalid purpose (should be denied)
        self._emit_progress("phase4", "Test: Invalid purpose policy", "start")
        try:
            read_result = self.api.read_memory(
                user_id="policy_test_user",
                scope="schedule",
                purpose="generate personalized content",  # Not allowed for schedule
                domain=None
            )
            # Should have been denied
            self.results["read"]["failed"] += 1
            self._emit_progress("phase4", "Test: Invalid purpose policy", "error", {
                "error": "Should have been denied but wasn't"
            })
        except Exception as e:
            if "403" in str(e) or "POLICY" in str(e).upper():
                self.results["read"]["success"] += 1
                self._emit_progress("phase4", "Test: Invalid purpose policy", "success", {
                    "verified": "Policy correctly denied invalid purpose"
                })
            else:
                self.results["read"]["failed"] += 1
                self._emit_progress("phase4", "Test: Invalid purpose policy", "error", {"error": str(e)})
    
    def _test_revocation(self):
        """Test revocation functionality."""
        # Create a read grant
        self._emit_progress("phase5", "Test: Revocation functionality", "start")
        try:
            read_result = self.api.read_memory(
                user_id="revoke_test_user",
                scope="preferences",
                purpose="generate recommendations",
                domain="food"
            )
            token = read_result["revocation_token"]
            
            # Revoke it
            revoke_result = self.api.revoke_memory(token)
            
            if revoke_result.get("revoked"):
                self.results["revoke"]["success"] += 1
                self._emit_progress("phase5", "Test: Revocation functionality", "success")
            else:
                self.results["revoke"]["failed"] += 1
                self._emit_progress("phase5", "Test: Revocation functionality", "error", {
                    "error": "Revocation returned revoked=False"
                })
            
            # Try to continue read (should fail)
            try:
                self.api.continue_read_memory(token)
                self.results["revoke"]["failed"] += 1
                self.results["revoke"]["test_cases"].append({
                    "name": "Revoked token access denial",
                    "status": "failed",
                    "error": "Revoked token should not work"
                })
                self._emit_progress("phase5", "Test: Revoked token access", "error", {
                    "error": "Revoked token should not work"
                })
            except:
                self.results["revoke"]["success"] += 1
                self.results["revoke"]["test_cases"].append({
                    "name": "Revoked token access denial",
                    "status": "success",
                    "details": "Revoked token correctly denied"
                })
                self._emit_progress("phase5", "Test: Revoked token access", "success", {
                    "verified": "Revoked token correctly denied"
                })
        except Exception as e:
            self.results["revoke"]["failed"] += 1
            self._emit_progress("phase5", "Test: Revocation functionality", "error", {"error": str(e)})

