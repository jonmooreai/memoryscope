import bcrypt
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from app.schemas import ALLOWED_PURPOSE_CLASSES, POLICY_MATRIX


def hash_api_key(api_key: str, salt_rounds: int = 12) -> str:
    """Hash an API key using bcrypt."""
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt(salt_rounds)).decode("utf-8")


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return bcrypt.checkpw(api_key.encode("utf-8"), api_key_hash.encode("utf-8"))


def hash_revocation_token(token: str) -> str:
    """Hash a revocation token using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_purpose(purpose: str) -> str:
    """Normalize purpose string to purpose_class."""
    purpose_lower = purpose.lower()
    # Simple keyword matching - can be enhanced
    if any(kw in purpose_lower for kw in ["content", "generate", "create", "write"]):
        return "content_generation"
    elif any(kw in purpose_lower for kw in ["recommend", "suggest", "recommendation"]):
        return "recommendation"
    elif any(kw in purpose_lower for kw in ["scheduling", "schedule", "calendar", "time"]):
        return "scheduling"
    elif any(kw in purpose_lower for kw in ["ui", "render", "display", "show"]):
        return "ui_rendering"
    elif any(kw in purpose_lower for kw in ["notify", "notification", "alert"]):
        return "notification_delivery"
    elif any(kw in purpose_lower for kw in ["task", "execute", "action", "run"]):
        return "task_execution"
    else:
        return "content_generation"  # default


def check_policy(scope: str, purpose_class: str) -> bool:
    """Check if purpose_class is allowed for the given scope."""
    allowed = POLICY_MATRIX.get(scope, set())
    return purpose_class in allowed


def normalize_value_json(value_json: Union[Dict[str, Any], List[Any]], shape: str) -> Union[Dict[str, Any], List[Any]]:
    """Normalize value_json: dedupe arrays, sort arrays, lowercase tags."""
    if shape == "likes_dislikes":
        if not isinstance(value_json, dict):
            return value_json
        result = {}
        if "likes" in value_json:
            # Dedupe case-insensitively, then sort
            seen = set()
            likes = []
            for item in value_json["likes"]:
                item_lower = item.lower() if isinstance(item, str) else item
                if item_lower not in seen:
                    seen.add(item_lower)
                    likes.append(item)
            likes.sort()
            result["likes"] = likes
        if "dislikes" in value_json:
            # Dedupe case-insensitively, then sort
            seen = set()
            dislikes = []
            for item in value_json["dislikes"]:
                item_lower = item.lower() if isinstance(item, str) else item
                if item_lower not in seen:
                    seen.add(item_lower)
                    dislikes.append(item)
            dislikes.sort()
            result["dislikes"] = dislikes
        return result
    elif shape == "rules_list":
        if not isinstance(value_json, list):
            return value_json
        rules = list(set(value_json))
        rules.sort()
        return rules
    elif shape == "schedule_windows":
        if isinstance(value_json, list):
            windows = list(value_json)
            # Dedupe by converting to tuples of sorted keys
            seen = set()
            deduped = []
            for window in windows:
                if isinstance(window, dict):
                    key = tuple(sorted(window.items()))
                    if key not in seen:
                        seen.add(key)
                        deduped.append(window)
                else:
                    deduped.append(window)
            return deduped
        elif isinstance(value_json, dict):
            return value_json
        return value_json
    elif shape == "boolean_flags":
        if not isinstance(value_json, dict):
            return value_json
        # Lowercase keys
        return {k.lower(): v for k, v in value_json.items()}
    elif shape == "attention_settings":
        if not isinstance(value_json, dict):
            return value_json
        # Lowercase keys and any tag-like values
        result = {}
        for k, v in value_json.items():
            key = k.lower()
            if isinstance(v, str):
                result[key] = v.lower()
            elif isinstance(v, list):
                result[key] = [item.lower() if isinstance(item, str) else item for item in v]
            else:
                result[key] = v
        return result
    else:  # kv_map
        if not isinstance(value_json, dict):
            return value_json
        # Lowercase keys
        result = {}
        for k, v in value_json.items():
            key = k.lower()
            if isinstance(v, str) and "tag" in key:
                result[key] = v.lower()
            else:
                result[key] = v
        return result


def _fuzzy_match_strings(str1: str, str2: str, threshold: float = 0.85) -> bool:
    """Check if two strings are similar enough to be considered the same (fuzzy matching)."""
    if not isinstance(str1, str) or not isinstance(str2, str):
        return False
    # Normalize: lowercase and strip
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()
    # Exact match after normalization
    if s1 == s2:
        return True
    # Check similarity ratio
    ratio = SequenceMatcher(None, s1, s2).ratio()
    return ratio >= threshold


def _dedupe_with_fuzzy(items: List[str], threshold: float = 0.85) -> List[str]:
    """Deduplicate list of strings using fuzzy matching."""
    if not items:
        return []
    result = []
    seen_normalized = set()
    seen_items = []
    
    for item in items:
        if not isinstance(item, str):
            result.append(item)
            continue
        item_lower = item.lower().strip()
        # Check for exact match (case-insensitive)
        if item_lower in seen_normalized:
            continue
        # Check for fuzzy match
        is_duplicate = False
        for seen in seen_items:
            if _fuzzy_match_strings(item, seen, threshold):
                is_duplicate = True
                break
        if not is_duplicate:
            result.append(item)
            seen_normalized.add(item_lower)
            seen_items.append(item)
    
    return sorted(result)


def merge_memories_deterministic(memories: List[Dict[str, Any]], scope: str) -> Dict[str, Any]:
    """
    Deterministically merge memories with fuzzy matching and return summary_text, summary_struct, confidence.
    
    Features:
    - Deterministic: Same memories always produce same result (sorted by created_at)
    - Fuzzy matching: Similar strings are treated as duplicates (e.g., "pizza" = "Pizza" = "pizzas", threshold: 0.85)
    - Key normalization: Similar keys are merged (e.g., "favorite_food" = "FavoriteFood" = "favorite-food")
    - Case-insensitive: All comparisons are case-insensitive
    - Deduplication: Duplicate values in arrays are removed using fuzzy matching
    """
    if not memories:
        return {
            "summary_text": "No memories found.",
            "summary_struct": {},
            "confidence": 0.0,
        }

    # Sort memories by created_at for determinism
    sorted_memories = sorted(memories, key=lambda m: (m["created_at"], str(m["id"])))

    # Merge based on scope
    if scope == "preferences":
        return _merge_preferences(sorted_memories)
    elif scope == "constraints":
        return _merge_constraints(sorted_memories)
    elif scope == "communication":
        return _merge_communication(sorted_memories)
    elif scope == "accessibility":
        return _merge_accessibility(sorted_memories)
    elif scope == "schedule":
        return _merge_schedule(sorted_memories)
    elif scope == "attention":
        return _merge_attention(sorted_memories)
    else:
        return {
            "summary_text": f"Unknown scope: {scope}",
            "summary_struct": {},
            "confidence": 0.0,
        }


def _merge_preferences(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge preferences memories with fuzzy matching for similar values."""
    all_likes = []
    all_dislikes = []
    kv_pairs = {}

    for mem in memories:
        value = mem["value_json"]
        shape = mem["value_shape"]
        if shape == "likes_dislikes" and isinstance(value, dict):
            # Collect all likes and dislikes (will dedupe with fuzzy matching later)
            all_likes.extend(value.get("likes", []))
            all_dislikes.extend(value.get("dislikes", []))
        elif shape == "kv_map" and isinstance(value, dict):
            # Merge kv_map: normalize keys (lowercase, remove underscores/spaces for matching)
            for k, v in value.items():
                key_lower = k.lower().strip()
                # Normalize key by removing underscores and spaces for matching
                key_normalized = key_lower.replace('_', '').replace(' ', '').replace('-', '')
                
                # Check if we have a similar key already
                matching_key = None
                for existing_key in kv_pairs.keys():
                    existing_normalized = existing_key.replace('_', '').replace(' ', '').replace('-', '')
                    if existing_normalized == key_normalized:
                        matching_key = existing_key
                        break
                
                if matching_key:
                    # Key already exists (normalized match)
                    existing = kv_pairs[matching_key]
                    if isinstance(existing, str) and isinstance(v, str):
                        if _fuzzy_match_strings(existing, v, threshold=0.9):
                            # Values are very similar, use the newer one
                            kv_pairs[matching_key] = v
                        else:
                            # Different values, keep the newer one (latest wins)
                            kv_pairs[matching_key] = v
                    else:
                        # Not both strings, just update (latest wins)
                        kv_pairs[matching_key] = v
                else:
                    # New key, add it
                    kv_pairs[key_lower] = v

    # Dedupe likes and dislikes with fuzzy matching
    deduped_likes = _dedupe_with_fuzzy([str(l) for l in all_likes if l is not None])
    deduped_dislikes = _dedupe_with_fuzzy([str(d) for d in all_dislikes if d is not None])

    summary_text = f"Likes: {len(deduped_likes)}, Dislikes: {len(deduped_dislikes)}, Settings: {len(kv_pairs)}"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {
        "likes": deduped_likes,
        "dislikes": deduped_dislikes,
        "settings": kv_pairs,
    }

    # Confidence based on recency and count
    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }


def _merge_constraints(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge constraints memories."""
    rules = []
    kv_pairs = {}

    for mem in memories:
        value = mem["value_json"]
        shape = mem["value_shape"]
        if shape == "rules_list":
            if isinstance(value, list):
                rules.extend(value)
        elif shape == "kv_map":
            if isinstance(value, dict):
                kv_pairs.update(value)

    rules = sorted(list(set(rules)))

    summary_text = f"Rules: {len(rules)}, Constraints: {len(kv_pairs)}"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {
        "rules": rules,
        "constraints": kv_pairs,
    }

    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }


def _merge_communication(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge communication memories."""
    kv_pairs = {}

    for mem in memories:
        value = mem["value_json"]
        if isinstance(value, dict):
            kv_pairs.update(value)

    summary_text = f"Communication preferences: {len(kv_pairs)} settings"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {"preferences": kv_pairs}

    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }


def _merge_accessibility(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge accessibility memories."""
    flags = {}
    kv_pairs = {}

    for mem in memories:
        value = mem["value_json"]
        shape = mem["value_shape"]
        if shape == "boolean_flags" and isinstance(value, dict):
            flags.update(value)
        elif isinstance(value, dict):
            kv_pairs.update(value)

    summary_text = f"Accessibility: {len(flags)} flags, {len(kv_pairs)} settings"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {
        "flags": flags,
        "settings": kv_pairs,
    }

    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }


def _merge_schedule(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge schedule memories."""
    windows = []

    for mem in memories:
        value = mem["value_json"]
        shape = mem["value_shape"]
        if shape == "schedule_windows":
            if isinstance(value, list):
                windows.extend(value)
            elif isinstance(value, dict):
                windows.append(value)

    # Dedupe windows
    seen = set()
    deduped = []
    for window in windows:
        if isinstance(window, dict):
            key = tuple(sorted(window.items()))
            if key not in seen:
                seen.add(key)
                deduped.append(window)
        else:
            deduped.append(window)

    summary_text = f"Schedule: {len(deduped)} time windows"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {"windows": deduped}

    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }


def _merge_attention(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge attention memories."""
    settings = {}

    for mem in memories:
        value = mem["value_json"]
        if isinstance(value, dict):
            settings.update(value)

    summary_text = f"Attention settings: {len(settings)} preferences"
    if len(summary_text) > 240:
        summary_text = summary_text[:237] + "..."

    summary_struct = {"settings": settings}

    confidence = min(0.9, 0.5 + len(memories) * 0.1)

    return {
        "summary_text": summary_text,
        "summary_struct": summary_struct,
        "confidence": confidence,
    }

