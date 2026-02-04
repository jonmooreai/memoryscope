#!/usr/bin/env python3
"""
Run the profile test questions and evaluate the memory system's responses.
This tests recall, inference, synthesis, and stress tests.
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_app.api_client import MemoryAPIClient
from test_app.config import config
from openai import OpenAI

QUESTIONS_FILE = Path(__file__).parent / "profile_test_questions.json"


def load_questions() -> List[Dict]:
    """Load test questions from JSON file."""
    with open(QUESTIONS_FILE) as f:
        data = json.load(f)
    return data["questions"]


def ask_question(question: str, user_id: str, api_client: MemoryAPIClient, openai_client: OpenAI) -> str:
    """Ask a question and get the AI's response using stored memories."""
    # First, retrieve relevant memories
    # We'll query all scopes to get comprehensive context
    scopes = ['preferences', 'constraints', 'communication', 'accessibility', 'schedule', 'attention']
    all_memories = []
    
    for scope in scopes:
        try:
            # Try to infer relevant domains from the question
            domain_prompt = f"""Analyze this question and determine which memory domains might be relevant: "{question}"

Common domains: food, work, personal, health, entertainment, family, travel, pets, hobbies, education, finance, shopping, social, relationships, lifestyle, finance, etc.

Return a JSON array of relevant domain names, or empty array if none are specific.

Return ONLY a JSON array:"""

            domain_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You analyze questions to determine relevant memory domains. Return only JSON arrays."},
                    {"role": "user", "content": domain_prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            domains_text = domain_response.choices[0].message.content.strip()
            try:
                domains = json.loads(domains_text)
                if not isinstance(domains, list):
                    domains = []
            except:
                domains = []
            
            # Query without domain first
            try:
                response = api_client.read_memory(
                    user_id=user_id,
                    scope=scope,
                    purpose="generate personalized content",
                    max_age_days=365
                )
                if response.get("summary_struct") and response["summary_struct"]:
                    all_memories.append({
                        "scope": scope,
                        "data": response["summary_struct"],
                        "confidence": response.get("confidence", 1.0)
                    })
            except:
                pass
            
            # Query with inferred domains
            for domain in domains:
                try:
                    response = api_client.read_memory(
                        user_id=user_id,
                        scope=scope,
                        domain=domain,
                        purpose="generate personalized content",
                        max_age_days=365
                    )
                    if response.get("summary_struct") and response["summary_struct"]:
                        # Merge with existing scope data
                        existing = next((m for m in all_memories if m["scope"] == scope), None)
                        if existing:
                            # Merge the data
                            existing_data = existing["data"]
                            new_data = response["summary_struct"]
                            if isinstance(existing_data, dict) and isinstance(new_data, dict):
                                # Simple merge
                                for k, v in new_data.items():
                                    if k in existing_data:
                                        if isinstance(existing_data[k], list) and isinstance(v, list):
                                            existing_data[k] = list(set(existing_data[k] + v))
                                        elif isinstance(existing_data[k], dict) and isinstance(v, dict):
                                            existing_data[k].update(v)
                                    else:
                                        existing_data[k] = v
                        else:
                            all_memories.append({
                                "scope": scope,
                                "data": response["summary_struct"],
                                "confidence": response.get("confidence", 1.0)
                            })
                except:
                    pass
        except Exception as e:
            print(f"  Warning: Error retrieving {scope} memories: {e}")
            continue
    
    # Build context with memories
    context = f"""You are a helpful AI assistant with access to the user's stored memories.

STORED MEMORIES:
"""
    if all_memories:
        for mem in all_memories:
            context += f"\n{mem['scope'].upper()} (confidence: {mem['confidence']:.2f}):\n"
            context += json.dumps(mem['data'], indent=2)
            context += "\n"
    else:
        context += "No memories stored yet.\n"
    
    context += f"""
CRITICAL INSTRUCTIONS:
1. ALWAYS check the stored memories above FIRST before answering
2. Be SPECIFIC and use exact details from memories when available
3. For inference questions, base your answer on patterns in the memories
4. If information is not in memories, say so explicitly
5. Quote specific details from memories when relevant

User question: {question}

Answer the question based on the stored memories above. Be specific and detailed."""

    # Get AI response
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": context}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def evaluate_answer(question_data: Dict, answer: str) -> Tuple[bool, str]:
    """Evaluate if the answer contains expected keywords and is appropriate."""
    expected_keywords = question_data.get("expected_keywords", [])
    answer_lower = answer.lower()
    
    found_keywords = []
    missing_keywords = []
    
    for keyword in expected_keywords:
        if keyword.lower() in answer_lower:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Score: at least 50% of keywords should be present for a pass
    score = len(found_keywords) / len(expected_keywords) if expected_keywords else 0
    passed = score >= 0.5
    
    evaluation = f"Found {len(found_keywords)}/{len(expected_keywords)} keywords"
    if missing_keywords:
        evaluation += f" (missing: {', '.join(missing_keywords[:3])})"
    
    return passed, evaluation


def run_tests(user_id: str = "profile_test_user", limit: int = None):
    """Run all test questions."""
    print("=" * 80)
    print("Profile Memory System Test Suite")
    print("=" * 80)
    print(f"User ID: {user_id}")
    print()
    
    # Initialize clients
    api_client = MemoryAPIClient(
        base_url=config.api_base_url,
        api_key=config.api_key
    )
    openai_client = OpenAI(api_key=config.openai_api_key)
    
    # Load questions
    questions = load_questions()
    if limit:
        questions = questions[:limit]
    
    print(f"Running {len(questions)} test questions...")
    print()
    
    results = {
        "total": len(questions),
        "passed": 0,
        "failed": 0,
        "by_category": {}
    }
    
    for i, question_data in enumerate(questions, 1):
        category = question_data["category"]
        question = question_data["question"]
        q_id = question_data["id"]
        
        print(f"[{i}/{len(questions)}] Q{q_id} ({category}): {question}")
        print("-" * 80)
        
        try:
            answer = ask_question(question, user_id, api_client, openai_client)
            print(f"Answer: {answer[:200]}...")
            print()
            
            passed, evaluation = evaluate_answer(question_data, answer)
            print(f"Evaluation: {'✓ PASS' if passed else '✗ FAIL'} - {evaluation}")
            
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            if category not in results["by_category"]:
                results["by_category"][category] = {"passed": 0, "failed": 0}
            if passed:
                results["by_category"][category]["passed"] += 1
            else:
                results["by_category"][category]["failed"] += 1
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results["failed"] += 1
        
        print()
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print()
    print("By Category:")
    for category, stats in results["by_category"].items():
        total = stats["passed"] + stats["failed"]
        pct = stats["passed"] / total * 100 if total > 0 else 0
        print(f"  {category}: {stats['passed']}/{total} ({pct:.1f}%)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run profile memory system tests")
    parser.add_argument("--user-id", default="profile_test_user", help="User ID to test (default: profile_test_user)")
    parser.add_argument("--limit", type=int, help="Limit number of questions to run")
    args = parser.parse_args()
    
    run_tests(args.user_id, args.limit)

