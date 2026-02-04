"""
MemoryScope Policy Engine
PRD v2.2 Section 9 - Policy DSL Implementation

Deterministic, fail-closed policy evaluation with full trace.
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import yaml
import json
from copy import deepcopy
from pydantic import BaseModel, Field

from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    Scope,
    PurposeType,
    SensitivityLevel,
    DisputeState,
)


class PolicyDecision(str, Enum):
    """Policy decision outcomes."""
    ALLOW = "allow"
    DENY = "deny"


class PolicyTrace(BaseModel):
    """Policy trace for every decision."""
    policy_version: str
    matched_rules: List[str] = Field(default_factory=list)  # Rule IDs in order
    final_decision: Dict[str, Any] = Field(default_factory=dict)
    denied_reasons: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyEngine:
    """
    Policy Engine - Deterministic, fail-closed evaluation.
    
    Features:
    - Versioned policies
    - Full trace for every decision
    - Deterministic evaluation (top-to-bottom, later overrides)
    - "Most restrictive wins" for allow/deny decisions
    """
    
    def __init__(self, policy_yaml: Optional[str] = None, policy_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize policy engine.
        
        Args:
            policy_yaml: YAML string of policy
            policy_dict: Pre-parsed policy dictionary
        """
        if policy_yaml:
            self.policy = yaml.safe_load(policy_yaml)
        elif policy_dict:
            self.policy = deepcopy(policy_dict)
        else:
            # Default policy
            self.policy = self._default_policy()
        
        self._validate_policy()
        self._compile_rules()
    
    def _default_policy(self) -> Dict[str, Any]:
        """Default policy (PRD v2.2 Section 9.2)."""
        return {
            "policy_version": "pol_2026_01_06_01",
            "defaults": {
                "write": "allow",
                "read": "deny",
                "include_in_prompt": "deny",
                "tool_execution": "allow",
                "reinforcement": "allow",
                "derive_impacts": "allow",
                "derive_seeds": "allow",
            },
            "globals": {
                "claimed_time_trust_threshold": 0.75,
                "spiral": {
                    "enabled_default": False,
                    "ttl_minutes": 45,
                    "block_tool_execution": True,
                    "block_reinforcement": True,
                    "block_new_impacts": True,
                    "raise_seed_activation_threshold_by": 0.15,
                },
            },
            "rules": [
                {
                    "id": "seal_sensitive_events",
                    "when": {
                        "memory.type": "event",
                        "memory.sensitivity.categories": ["trauma", "shame", "moral_injury"],
                    },
                    "then": {
                        "set_state": "sealed",
                        "allow_read": False,
                        "include_in_prompt": False,
                        "derive_impacts": True,
                        "derive_seeds": True,
                    },
                },
                {
                    "id": "allow_impacts_for_chat",
                    "when": {
                        "memory.type": "impact",
                        "request.purpose": "chat_response",
                        "memory.sensitivity.level": ["low", "medium"],
                    },
                    "then": {
                        "allow_read": True,
                        "include_in_prompt": True,
                    },
                },
                {
                    "id": "deny_disputed_facts_in_chat",
                    "when": {
                        "memory.truth_mode": "factual_claim",
                        "memory.ownership.dispute_state": ["disputed", "contested"],
                        "request.purpose": "chat_response",
                    },
                    "then": {
                        "allow_read": False,
                    },
                },
                {
                    "id": "deny_nonfactual_for_tools",
                    "when": {
                        "memory.truth_mode": ["counterfactual", "imagined", "socially_sourced"],
                        "request.purpose": "task_execution",
                    },
                    "then": {
                        "allow_read": False,
                    },
                },
            ],
        }
    
    def _validate_policy(self):
        """Validate policy structure."""
        required_keys = ["policy_version", "defaults", "rules"]
        for key in required_keys:
            if key not in self.policy:
                raise ValueError(f"Policy missing required key: {key}")
        
        # Validate defaults
        defaults = self.policy["defaults"]
        allowed_defaults = ["write", "read", "include_in_prompt", "tool_execution", 
                           "reinforcement", "derive_impacts", "derive_seeds"]
        for key in defaults:
            if key not in allowed_defaults:
                raise ValueError(f"Unknown default key: {key}")
            if defaults[key] not in ["allow", "deny"]:
                raise ValueError(f"Default value must be 'allow' or 'deny': {key}={defaults[key]}")
    
    def _compile_rules(self):
        """Compile rules for faster evaluation."""
        self.compiled_rules = []
        for rule in self.policy.get("rules", []):
            compiled = {
                "id": rule["id"],
                "when": self._compile_conditions(rule.get("when", {})),
                "then": rule.get("then", {}),
            }
            self.compiled_rules.append(compiled)
    
    def _compile_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Compile conditions for evaluation."""
        compiled = {}
        for key, value in conditions.items():
            # Support dot notation: "memory.type" -> nested access
            compiled[key] = value
        return compiled
    
    def _match_condition(self, condition_key: str, condition_value: Any, context: Dict[str, Any]) -> bool:
        """
        Match a single condition against context.
        
        Supports:
        - Dot notation: "memory.type" -> context["memory"]["type"]
        - List values: ["value1", "value2"] matches if actual value in list
        - Single values: "value" matches if actual value equals
        """
        # Resolve nested path
        parts = condition_key.split(".")
        actual_value = context
        for part in parts:
            if not isinstance(actual_value, dict):
                return False
            actual_value = actual_value.get(part)
            if actual_value is None:
                return False
        
        # Match value
        if isinstance(condition_value, list):
            return actual_value in condition_value
        else:
            return actual_value == condition_value
    
    def _match_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if a rule matches the context."""
        when = rule["when"]
        for condition_key, condition_value in when.items():
            if not self._match_condition(condition_key, condition_value, context):
                return False
        return True
    
    def evaluate_ingest(
        self,
        memory: MemoryObject,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate policy for memory ingestion.
        
        Returns:
            {
                "allowed": bool,
                "state": MemoryState,
                "derive_impacts": bool,
                "derive_seeds": bool,
                "trace": PolicyTrace,
            }
        """
        if context is None:
            context = {}
        
        context["memory"] = {
            "type": memory.type.value,
            "truth_mode": memory.truth_mode.value,
            "state": memory.state.value,
            "sensitivity": {
                "level": memory.sensitivity.level.value,
                "categories": memory.sensitivity.categories,
                "handling": memory.sensitivity.handling.value,
            },
            "ownership": {
                "dispute_state": memory.ownership.dispute_state.value,
            },
        }
        
        # Start with defaults
        decision = {
            "allowed": self.policy["defaults"]["write"] == "allow",
            "state": memory.state,
            "derive_impacts": self.policy["defaults"]["derive_impacts"] == "allow",
            "derive_seeds": self.policy["defaults"]["derive_seeds"] == "allow",
        }
        
        matched_rules = []
        denied_reasons = []
        
        # Evaluate rules top-to-bottom
        for rule in self.compiled_rules:
            if self._match_rule(rule, context):
                matched_rules.append(rule["id"])
                then = rule["then"]
                
                # Apply "then" actions
                if "set_state" in then:
                    decision["state"] = MemoryState(then["set_state"])
                
                if "allow_read" in then:
                    # This is for read evaluation, not ingest
                    pass
                
                if "derive_impacts" in then:
                    decision["derive_impacts"] = then["derive_impacts"] is True
                
                if "derive_seeds" in then:
                    decision["derive_seeds"] = then["derive_seeds"] is True
                
                if "allow_read" in then and then["allow_read"] is False:
                    denied_reasons.append(f"Rule {rule['id']}: read denied")
        
        trace = PolicyTrace(
            policy_version=self.policy["policy_version"],
            matched_rules=matched_rules,
            final_decision=decision,
            denied_reasons=denied_reasons,
        )
        
        decision["trace"] = trace
        return decision
    
    def evaluate_query(
        self,
        memory: MemoryObject,
        purpose: PurposeType,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate policy for memory query/retrieval.
        
        Returns:
            {
                "allowed": bool,
                "include_in_prompt": bool,
                "trace": PolicyTrace,
            }
        """
        if context is None:
            context = {}
        
        context["memory"] = {
            "type": memory.type.value,
            "truth_mode": memory.truth_mode.value,
            "state": memory.state.value,
            "sensitivity": {
                "level": memory.sensitivity.level.value,
                "categories": memory.sensitivity.categories,
            },
            "ownership": {
                "dispute_state": memory.ownership.dispute_state.value,
            },
        }
        context["request"] = {
            "purpose": purpose.value,
        }
        
        # Start with defaults
        decision = {
            "allowed": self.policy["defaults"]["read"] == "allow",
            "include_in_prompt": self.policy["defaults"]["include_in_prompt"] == "allow",
        }
        
        matched_rules = []
        denied_reasons = []
        
        # Track most restrictive decision for allow/deny
        allow_decisions = []
        include_decisions = []
        
        # Evaluate rules top-to-bottom
        for rule in self.compiled_rules:
            if self._match_rule(rule, context):
                matched_rules.append(rule["id"])
                then = rule["then"]
                
                # Apply "then" actions
                if "allow_read" in then:
                    allow_decisions.append(then["allow_read"])
                
                if "include_in_prompt" in then:
                    include_decisions.append(then["include_in_prompt"])
        
        # Most restrictive wins
        if allow_decisions:
            decision["allowed"] = all(allow_decisions)  # All must be True
            if not decision["allowed"]:
                denied_reasons.append("Rule denied read access")
        
        if include_decisions:
            decision["include_in_prompt"] = all(include_decisions)  # All must be True
        
        trace = PolicyTrace(
            policy_version=self.policy["policy_version"],
            matched_rules=matched_rules,
            final_decision=decision,
            denied_reasons=denied_reasons,
        )
        
        decision["trace"] = trace
        return decision
    
    def evaluate_tool_execution(
        self,
        memories: List[MemoryObject],
        purpose: PurposeType,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate policy for tool execution.
        
        Returns:
            {
                "allowed": bool,
                "denied_memory_ids": List[str],
                "trace": PolicyTrace,
            }
        """
        if context is None:
            context = {}
        
        context["request"] = {
            "purpose": purpose.value,
        }
        
        allowed_memories = []
        denied_memory_ids = []
        matched_rules = []
        denied_reasons = []
        
        for memory in memories:
            context["memory"] = {
                "type": memory.type.value,
                "truth_mode": memory.truth_mode.value,
                "state": memory.state.value,
            }
            
            # Check if this memory can be used for tool execution
            memory_allowed = True
            
            # Rule: deny_nonfactual_for_tools
            if purpose == PurposeType.TASK_EXECUTION:
                if memory.truth_mode in [TruthMode.COUNTERFACTUAL, TruthMode.IMAGINED, TruthMode.SOCIALLY_SOURCED]:
                    memory_allowed = False
                    denied_reasons.append(f"Memory {memory.id}: nonfactual truth_mode cannot be used for tool execution")
            
            if memory_allowed:
                allowed_memories.append(memory)
            else:
                denied_memory_ids.append(memory.id)
        
        decision = {
            "allowed": len(allowed_memories) > 0,
            "allowed_memory_ids": [m.id for m in allowed_memories],
            "denied_memory_ids": denied_memory_ids,
        }
        
        trace = PolicyTrace(
            policy_version=self.policy["policy_version"],
            matched_rules=matched_rules,
            final_decision=decision,
            denied_reasons=denied_reasons,
        )
        
        decision["trace"] = trace
        return decision
    
    def get_spiral_config(self) -> Dict[str, Any]:
        """Get spiral detection configuration from globals."""
        return self.policy.get("globals", {}).get("spiral", {
            "enabled_default": False,
            "ttl_minutes": 45,
            "block_tool_execution": True,
            "block_reinforcement": True,
            "block_new_impacts": True,
            "raise_seed_activation_threshold_by": 0.15,
        })
    
    def get_policy_version(self) -> str:
        """Get policy version."""
        return self.policy["policy_version"]


# Import Pydantic BaseModel
from pydantic import BaseModel, Field

