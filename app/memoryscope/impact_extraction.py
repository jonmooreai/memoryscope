"""
MemoryScope v2 Impact Extraction

Deterministic extraction of impacts (constraints) from events (PRD v2.2 Section 3.5).

Key requirements:
- Deterministic: Same event always produces same impacts
- Narrative-free: Constraints must be atomic, no raw narrative text
- No sealed content: Never extract from sealed event narrative
- Versioned transforms: Transform version pinned in provenance
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from sqlalchemy.orm import Session

from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    Constraint,
    ConstraintKind,
    ConstraintTarget,
    ConstraintMerge,
    MergeStrategy,
    Scope,
    SensitivityLevel,
    generate_constraint_id,
    generate_memory_id,
    ImpactPayload,
    Provenance,
    SourceType,
)


class ImpactExtractor:
    """
    Deterministic impact extraction from events.
    
    Extracts constraints from events following PRD v2.2 Section 3.5.
    All extraction is deterministic and narrative-free.
    """
    
    def __init__(self, transform_version: str = "tx_impact_extract_v2.1.0"):
        self.transform_version = transform_version
    
    def extract_impacts(
        self,
        event: MemoryObject,
        policy_allows: bool = True,
    ) -> Optional[MemoryObject]:
        """
        Extract impacts from an event.
        
        Args:
            event: Event memory to extract from
            policy_allows: Whether policy allows impact derivation
        
        Returns:
            Impact memory object, or None if extraction not possible
        """
        if not policy_allows:
            return None
        
        # Cannot extract from sealed events (safety requirement)
        if event.state == MemoryState.SEALED:
            return None
        
        # Cannot extract from nonfactual events for certain purposes
        # (But we allow extraction for tone/style constraints)
        if event.truth_mode in [TruthMode.COUNTERFACTUAL, TruthMode.IMAGINED]:
            # Only extract tone/style constraints, not factual constraints
            pass
        
        # Extract constraints based on event content and sensitivity
        constraints = []
        
        # Extract safety constraints from sensitive events
        if event.sensitivity.level in [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]:
            if "trauma" in event.sensitivity.categories:
                constraints.append(self._create_safety_constraint(
                    event=event,
                    mode="supportive_reframe_only",
                    consent_required=True,
                ))
            
            if "shame" in event.sensitivity.categories or "moral_injury" in event.sensitivity.categories:
                constraints.append(self._create_avoid_constraint(
                    event=event,
                    content_class="judgment_language",
                ))
                constraints.append(self._create_tone_constraint(
                    event=event,
                    tone_profile="non_judgmental",
                ))
        
        # Extract communication preferences from communication events
        if event.type == MemoryType.EVENT:
            content_text = event.content.text or ""
            
            # Extract tone preferences
            if self._detect_tone_preference(content_text):
                tone = self._detect_tone_preference(content_text)
                constraints.append(self._create_tone_constraint(
                    event=event,
                    tone_profile=tone,
                ))
            
            # Extract style preferences
            if self._detect_style_preference(content_text):
                style = self._detect_style_preference(content_text)
                constraints.append(self._create_style_constraint(
                    event=event,
                    format=style,
                ))
        
        # If no constraints extracted, return None
        if not constraints:
            return None
        
        # Create impact memory
        impact_id = generate_memory_id()
        impact_memory = MemoryObject(
            id=impact_id,
            tenant_id=event.tenant_id,
            scope=event.scope,
            type=MemoryType.IMPACT,
            truth_mode=TruthMode.PROCEDURAL,  # Impacts are procedural
            state=MemoryState.ACTIVE,
            sensitivity=event.sensitivity,  # Inherit sensitivity
            ownership=event.ownership,  # Inherit ownership
            temporal=event.temporal,  # Inherit temporal
            content=event.content,  # Can reference original content
            affect=event.affect,  # Inherit affect
            impact_payload=ImpactPayload(constraints=constraints),
            strength=event.strength,  # Inherit strength
            provenance=Provenance(
                source=SourceType.SYSTEM,
                derived_from=[event.id],
                transform_chain=[{
                    "transform_id": self.transform_version,
                    "version": self.transform_version.split("_v")[-1] if "_v" in self.transform_version else "2.1.0",
                    "run_id": f"run_{datetime.utcnow().isoformat()}",
                }],
                policy_version=event.provenance.policy_version,
                confidence=0.7,  # Moderate confidence for extracted impacts
            ),
            reconsolidation_policy="append_only",  # Impacts are append-only
        )
        
        return impact_memory
    
    def _create_safety_constraint(
        self,
        event: MemoryObject,
        mode: str,
        consent_required: bool = True,
    ) -> Dict[str, Any]:
        """Create a safety constraint."""
        return {
            "constraint_id": generate_constraint_id(),
            "kind": ConstraintKind.SAFETY.value,
            "topic": "safety",
            "target": ConstraintTarget.RESPONSE.value,
            "rule": "safety_extraction_v2",
            "params": {
                "mode": mode,
                "consent_required": consent_required,
            },
            "weight": 1.0,
            "priority": 10,
            "confidence": 0.8,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": None,
            "source_refs": [event.id],
            "provenance": {
                "transform_id": self.transform_version,
                "policy_version": event.provenance.policy_version,
            },
            "merge": {
                "slot": "safety",
                "strategy": MergeStrategy.MOST_RESTRICTIVE_WINS.value if hasattr(MergeStrategy, "MOST_RESTRICTIVE_WINS") else MergeStrategy.INTERSECTION.value,
                "tie_breakers": ["priority", "created_at"],
            },
        }
    
    def _create_avoid_constraint(
        self,
        event: MemoryObject,
        content_class: str,
    ) -> Dict[str, Any]:
        """Create an avoid constraint."""
        return {
            "constraint_id": generate_constraint_id(),
            "kind": ConstraintKind.AVOID.value,
            "topic": "content",
            "target": ConstraintTarget.RESPONSE.value,
            "rule": "avoid_extraction_v2",
            "params": {
                "content_class": content_class,
            },
            "weight": 0.9,
            "priority": 8,
            "confidence": 0.75,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": None,
            "source_refs": [event.id],
            "provenance": {
                "transform_id": self.transform_version,
                "policy_version": event.provenance.policy_version,
            },
            "merge": {
                "slot": "avoid",
                "strategy": MergeStrategy.INTERSECTION.value,
                "tie_breakers": ["priority", "created_at"],
            },
        }
    
    def _create_tone_constraint(
        self,
        event: MemoryObject,
        tone_profile: str,
    ) -> Dict[str, Any]:
        """Create a tone constraint."""
        return {
            "constraint_id": generate_constraint_id(),
            "kind": ConstraintKind.TONE.value,
            "topic": "tone",
            "target": ConstraintTarget.RESPONSE.value,
            "rule": "tone_extraction_v2",
            "params": {
                "tone_profile": tone_profile,
            },
            "weight": 0.7,
            "priority": 5,
            "confidence": 0.7,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": None,
            "source_refs": [event.id],
            "provenance": {
                "transform_id": self.transform_version,
                "policy_version": event.provenance.policy_version,
            },
            "merge": {
                "slot": "tone",
                "strategy": MergeStrategy.LATEST_WINS.value,
                "tie_breakers": ["priority", "created_at"],
            },
        }
    
    def _create_style_constraint(
        self,
        event: MemoryObject,
        format: str,
    ) -> Dict[str, Any]:
        """Create a style constraint."""
        return {
            "constraint_id": generate_constraint_id(),
            "kind": ConstraintKind.STYLE.value,
            "topic": "style",
            "target": ConstraintTarget.RESPONSE.value,
            "rule": "style_extraction_v2",
            "params": {
                "format": format,
            },
            "weight": 0.6,
            "priority": 4,
            "confidence": 0.65,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": None,
            "source_refs": [event.id],
            "provenance": {
                "transform_id": self.transform_version,
                "policy_version": event.provenance.policy_version,
            },
            "merge": {
                "slot": "style",
                "strategy": MergeStrategy.UNION.value,
                "tie_breakers": ["priority", "created_at"],
            },
        }
    
    def _detect_tone_preference(self, text: str) -> Optional[str]:
        """
        Detect tone preference from text (deterministic).
        
        This is a simple rule-based approach. In production, this could
        use more sophisticated NLP, but must remain deterministic.
        """
        text_lower = text.lower()
        
        # Simple keyword matching (deterministic)
        if any(word in text_lower for word in ["gentle", "soft", "kind", "caring"]):
            return "reassuring"
        elif any(word in text_lower for word in ["direct", "straightforward", "clear"]):
            return "matter_of_fact"
        elif any(word in text_lower for word in ["supportive", "helpful", "encouraging"]):
            return "supportive"
        elif any(word in text_lower for word in ["firm", "strict", "serious"]):
            return "firm"
        
        return None
    
    def _detect_style_preference(self, text: str) -> Optional[str]:
        """
        Detect style preference from text (deterministic).
        """
        text_lower = text.lower()
        
        # Check for bullet points or lists
        if re.search(r'[•\-\*]\s', text) or "bullet" in text_lower:
            return "bullets"
        elif re.search(r'\d+\.\s', text) or "numbered" in text_lower:
            return "numbered_steps"
        elif len(text.split('\n\n')) > 3 or "paragraph" in text_lower:
            return "short_paragraphs"
        
        return None


def extract_and_store_impact(
    db: Session,
    event: MemoryObject,
    app_id: str,
    extractor: ImpactExtractor,
    policy_allows: bool = True,
) -> Optional[MemoryObject]:
    """
    Extract impact from event and store it.
    
    Returns the created impact memory, or None if extraction not possible.
    """
    impact = extractor.extract_impacts(event, policy_allows)
    
    if impact is None:
        return None
    
    # Store impact
    from app.memoryscope.storage import store_memory
    store_memory(db, impact, app_id)
    
    # Create link between event and impact
    from app.memoryscope.core_types import DerivedObjectLink
    from app.memoryscope.storage import store_memory_link
    
    link = DerivedObjectLink(
        parent_id=event.id,
        child_id=impact.id,
        relationship="derived_impact",
        rule=extractor.transform_version,
        strength_transfer=0.4,
        created_at=datetime.utcnow(),
    )
    store_memory_link(db, link)
    
    return impact

