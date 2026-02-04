#!/usr/bin/env python3
"""
Load a user profile and extract structured memories from it.
This script uses OpenAI to intelligently extract memories from a detailed profile.
"""
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_app.api_client import MemoryAPIClient
from test_app.config import config
from openai import OpenAI

PROFILE = """I'm 38, born in a small coastal town and raised mostly by practical people who valued showing up over talking about feelings. My parents are still together. They're different in every way, which taught me early how compromise actually works, not the tidy version people describe. I'm close with my sister. We don't talk every day, but when we do it's honest and usually useful.

I live in a mid-sized city now, not because it was a dream but because it offers enough without demanding everything. I like walkable neighborhoods, old houses with character, and grocery stores that don't feel like warehouses. I prefer quiet mornings, strong coffee, and routines that leave room for improvisation later in the day.

Professionally, I work in product operations, the space between ideas and reality. I'm good at translating vague goals into systems people can actually use. I didn't plan this career. I studied sociology, bounced through a few jobs that looked better on paper than they felt, and slowly realized I was most valuable when I reduced friction for others. I'm not flashy at work, but I'm dependable. People tend to trust me with complicated things they don't want to break.

I'm married. We've been together long enough that romance looks less like surprises and more like mutual maintenance. We're different thinkers. That causes friction sometimes, but it also keeps us honest. No kids yet. We're undecided, and we're okay admitting that instead of pretending certainty will arrive later.

I'm financially cautious, sometimes to a fault. I save more than I spend, track where my money goes, and dislike lifestyle inflation. I'm willing to pay for quality and time, but not status. I don't mind used things. I do mind waste.

Socially, I'm selective. I enjoy people, but I need space to reset. Small groups over crowds. Long conversations over small talk. I'm loyal once trust is established, slow before that. I don't enjoy conflict, but I won't avoid it if something important is at stake.

My interests are ordinary but taken seriously. I cook most nights and treat it as a craft, not a performance. I like books that explain how things work, both mechanically and psychologically. I walk a lot, partly for health, partly to think. I listen more than I speak, which sometimes gets mistaken for agreement when it isn't.

Politically, I'm pragmatic. Ideology matters less to me than outcomes and incentives. I'm skeptical of simple answers and suspicious of moral certainty. I try to change my mind when evidence warrants it, though I don't always succeed.

I'm not especially nostalgic, but I do think a lot about time. What compounds. What doesn't. What's reversible and what isn't. I try to build my life around optionality, keeping doors open without standing frozen in the hallway.

If there's a throughline, it's this: I care about systems, relationships, and decisions that hold up over time. I'm less interested in being impressive than in being useful, steady, and hard to knock over when things get messy."""


def extract_memories_from_profile(profile_text: str, openai_client: OpenAI) -> list:
    """Extract structured memories from a profile using OpenAI."""
    prompt = f"""Analyze this detailed user profile and extract ALL relevant information as structured memories.

Profile:
{profile_text}

Extract memories in this JSON format:
{{
  "memories": [
    {{
      "scope": "preferences|constraints|communication|accessibility|schedule|attention",
      "domain": "optional domain like 'food', 'work', 'family', 'lifestyle', 'finance', etc.",
      "value": {{ ... }}
    }}
  ]
}}

IMPORTANT RULES:
1. Extract ALL factual information, preferences, constraints, and personal details
2. Use appropriate scopes:
   - preferences: likes, dislikes, preferences (e.g., walkable neighborhoods, strong coffee, quiet mornings)
   - constraints: rules, limitations, boundaries (e.g., financial caution, selective socializing)
   - communication: family relationships, social preferences, communication style
   - accessibility: not applicable here
   - schedule: routines, time preferences
   - attention: focus preferences, social energy needs

3. Use appropriate domains to organize memories (e.g., 'family', 'work', 'lifestyle', 'finance', 'social', 'hobbies')

4. Value shapes must match:
   - For preferences: {{"likes": [...], "dislikes": [...]}} OR {{"key": "value"}} (kv_map)
   - For constraints: ["rule1", "rule2"] OR {{"key": "value"}} (kv_map)
   - For communication: {{"key": "value"}} (kv_map)
   - For schedule: [{{"day": "monday", "start": "09:00", "end": "17:00"}}] OR {{"key": "value"}} (kv_map)
   - For attention: {{"key": "value"}} (kv_map)

5. Be comprehensive - extract as many memories as possible from the profile
6. Group related information logically
7. Use clear, descriptive keys for kv_map values

Return ONLY valid JSON. Extract as many memories as needed to capture all the information."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a memory extraction system. Extract comprehensive, structured memories from user profiles. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("memories", [])
    except Exception as e:
        print(f"Error extracting memories: {e}")
        return []


def load_profile(user_id: str = "profile_test_user"):
    """Load the profile and store all extracted memories."""
    print("Loading profile and extracting memories...")
    print(f"User ID: {user_id}")
    print()
    
    # Initialize clients
    api_client = MemoryAPIClient(
        base_url=config.api_base_url,
        api_key=config.api_key
    )
    openai_client = OpenAI(api_key=config.openai_api_key)
    
    # Extract memories
    print("Extracting memories from profile...")
    memories = extract_memories_from_profile(PROFILE, openai_client)
    print(f"Extracted {len(memories)} memories")
    print()
    
    # Store memories
    stored_count = 0
    failed_count = 0
    
    for i, memory in enumerate(memories, 1):
        try:
            scope = memory.get("scope")
            domain = memory.get("domain")
            value = memory.get("value")
            
            if not scope or not value:
                print(f"  [{i}] Skipping invalid memory (missing scope or value)")
                failed_count += 1
                continue
            
            print(f"  [{i}] Storing {scope}/{domain or 'no domain'}: {json.dumps(value)[:80]}...")
            
            response = api_client.create_memory(
                user_id=user_id,
                scope=scope,
                domain=domain,
                source="explicit_user_input",
                ttl_days=365,
                value_json=value
            )
            
            stored_count += 1
            print(f"      ✓ Stored (ID: {response['id'][:8]}...)")
            
        except Exception as e:
            print(f"      ✗ Failed: {e}")
            failed_count += 1
    
    print()
    print(f"Summary:")
    print(f"  Total extracted: {len(memories)}")
    print(f"  Successfully stored: {stored_count}")
    print(f"  Failed: {failed_count}")
    print()
    print(f"Profile loaded! Use user_id '{user_id}' in the chat demo to test.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load a user profile into the memory system")
    parser.add_argument("--user-id", default="profile_test_user", help="User ID to use (default: profile_test_user)")
    args = parser.parse_args()
    
    load_profile(args.user_id)

