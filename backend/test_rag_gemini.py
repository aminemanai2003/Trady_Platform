"""
Test script for RAG system with new Gemini SDK.
Tests embedding generation and text generation.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from rag_tutor.services.gemini_service import get_embedding, generate_answer


def test_embeddings():
    """Test embedding generation."""
    print("\n" + "="*60)
    print("TEST 1: Embedding Generation")
    print("="*60)
    
    test_text = "What is forex trading?"
    
    try:
        embedding = get_embedding(test_text, task_type="RETRIEVAL_QUERY")
        print(f"✓ Successfully generated embedding")
        print(f"  Text: '{test_text}'")
        print(f"  Embedding dimensions: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        return True
    except Exception as e:
        print(f"✗ Failed to generate embedding: {e}")
        return False


def test_generation():
    """Test text generation."""
    print("\n" + "="*60)
    print("TEST 2: Text Generation")
    print("="*60)
    
    query = "What is a pip in forex?"
    context = [
        "A pip is the smallest price move that a given exchange rate can make. "
        "Most currency pairs are priced to four decimal places."
    ]
    
    try:
        result = generate_answer(query, context, user_id="test_user")
        print(f"✓ Successfully generated answer")
        print(f"  Query: '{query}'")
        print(f"  Answer: {result['answer'][:200]}...")
        print(f"  Cached: {result['cached']}")
        return True
    except Exception as e:
        print(f"✗ Failed to generate answer: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING RAG SYSTEM WITH GEMINI API")
    print("="*60)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("✗ GEMINI_API_KEY not set in environment!")
        return False
    
    print(f"✓ API Key found: {api_key[:20]}...")
    
    # Run tests
    tests = [
        test_embeddings,
        test_generation,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
