"""
OpenAI client for generating realistic test data.
"""
import json
import random
from typing import Dict, Any, List, Optional
from openai import OpenAI

from test_app.config import config


class OpenAIDataGenerator:
    """Generate realistic test data using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key or config.openai_api_key)
        self.model = config.openai_model
    
    def generate_memory_value(
        self, 
        scope: str, 
        domain: Optional[str] = None,
        value_shape: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a realistic memory value for the given scope.
        
        Args:
            scope: Memory scope (preferences, constraints, etc.)
            domain: Optional domain (food, work, etc.)
            value_shape: Optional specific shape to generate
            
        Returns:
            Generated value_json that matches the API's expected shapes
        """
        # Determine which shapes are valid for this scope
        if value_shape:
            shapes = [value_shape]
        else:
            # Generate a random valid shape for this scope
            if scope == "preferences":
                shapes = ["likes_dislikes", "kv_map"]
            elif scope == "constraints":
                shapes = ["rules_list", "kv_map"]
            elif scope == "communication":
                shapes = ["kv_map"]
            elif scope == "accessibility":
                shapes = ["boolean_flags", "kv_map"]
            elif scope == "schedule":
                shapes = ["schedule_windows"]
            elif scope == "attention":
                shapes = ["attention_settings", "kv_map"]
            else:
                shapes = ["kv_map"]
            
            value_shape = random.choice(shapes)
        
        # Generate based on shape
        if value_shape == "likes_dislikes":
            return self._generate_likes_dislikes(scope, domain)
        elif value_shape == "rules_list":
            return self._generate_rules_list(scope, domain)
        elif value_shape == "schedule_windows":
            return self._generate_schedule_windows(scope, domain)
        elif value_shape == "boolean_flags":
            return self._generate_boolean_flags(scope, domain)
        elif value_shape == "attention_settings":
            return self._generate_attention_settings(scope, domain)
        else:  # kv_map
            return self._generate_kv_map(scope, domain)
    
    def _generate_likes_dislikes(self, scope: str, domain: Optional[str]) -> Dict[str, Any]:
        """Generate likes/dislikes using OpenAI."""
        prompt = f"""Generate a realistic JSON object with "likes" and "dislikes" arrays for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY valid JSON in this exact format:
{{
  "likes": ["item1", "item2", ...],
  "dislikes": ["item1", "item2", ...]
}}

Make it realistic and specific. Include 3-8 items in each array."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic user preference data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def _generate_rules_list(self, scope: str, domain: Optional[str]) -> List[str]:
        """Generate rules list using OpenAI."""
        prompt = f"""Generate a realistic list of rules/constraints for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY a valid JSON array of strings, like:
["rule 1", "rule 2", "rule 3"]

Make it realistic and specific. Include 3-6 rules."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic user constraint data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def _generate_schedule_windows(self, scope: str, domain: Optional[str]) -> List[Dict[str, Any]]:
        """Generate schedule windows using OpenAI."""
        prompt = f"""Generate a realistic list of schedule time windows for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY valid JSON array of objects, like:
[
  {{"day": "monday", "start": "09:00", "end": "17:00"}},
  {{"day": "tuesday", "start": "09:00", "end": "17:00"}}
]

Make it realistic. Include 2-5 time windows."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic schedule data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def _generate_boolean_flags(self, scope: str, domain: Optional[str]) -> Dict[str, Any]:
        """Generate boolean flags using OpenAI."""
        prompt = f"""Generate a realistic JSON object with boolean flags for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY valid JSON object with boolean values, like:
{{
  "flag1": true,
  "flag2": false,
  "flag3": true
}}

Make it realistic and specific. Include 3-6 flags."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic boolean flag data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def _generate_attention_settings(self, scope: str, domain: Optional[str]) -> Dict[str, Any]:
        """Generate attention settings using OpenAI."""
        prompt = f"""Generate a realistic JSON object for attention/focus settings for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY valid JSON object, like:
{{
  "focus_mode": true,
  "do_not_disturb": false,
  "notification_sound": "gentle"
}}

Make it realistic. Include 2-5 settings."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic attention setting data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def _generate_kv_map(self, scope: str, domain: Optional[str]) -> Dict[str, Any]:
        """Generate key-value map using OpenAI."""
        prompt = f"""Generate a realistic JSON object with key-value pairs for a user's {scope} preferences.
{f'Focus on the {domain} domain.' if domain else ''}

Return ONLY valid JSON object, like:
{{
  "key1": "value1",
  "key2": 42,
  "key3": true
}}

Make it realistic and specific. Include 3-6 key-value pairs. Use appropriate types (strings, numbers, booleans)."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic preference data. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    def generate_user_profile(self) -> Dict[str, Any]:
        """Generate a realistic user profile for context."""
        prompt = """Generate a brief, realistic user profile (2-3 sentences) describing a person's general preferences and characteristics.
This will be used to generate consistent test data.

Return ONLY plain text, no JSON, no formatting."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates realistic user profiles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()

