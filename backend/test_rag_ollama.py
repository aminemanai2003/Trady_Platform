"""
Test script for RAG system with Ollama + HuggingFace fallback.
Tests embedding generation and text generation with automatic fallback.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from rag_tutor.services.ollama_service import (
    get_embedding, 
    generate_answer,
    _check_ollama_available
)


def test_ollama_detection():
    """Test if Ollama is running."""
    print("\n" + "="*60)
    print("TEST 1: Ollama Detection")
    print("="*60)
    
    is_available = _check_ollama_available()
    if is_available:
        print("✓ Ollama is running at http://localhost:11434")
        print("  Will use Ollama for embeddings and generation")
    else:
        print("⚠ Ollama not detected")
        print("  Will fall back to HuggingFace (local, CPU)")
        print("  Install Ollama: https://ollama.ai/download")
    
    return True


def test_embeddings():
    """Test embedding generation with fallback."""
    print("\n" + "="*60)
    print("TEST 2: Embedding Generation")
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
        print(f"  Make sure sentence-transformers is installed:")
        print(f"  pip install sentence-transformers")
        return False


def test_generation():
    """Test text generation with fallback."""
    print("\n" + "="*60)
    print("TEST 3: Text Generation")
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
        print(f"  Provider: {result.get('provider', 'unknown')}")
        print(f"  Answer: {result['answer'][:200]}...")
        print(f"  Cached: {result['cached']}")
        
        if "temporarily unavailable" in result['answer']:
            print("\n  ⚠ Both Ollama and HuggingFace failed")
            print("  Install Ollama or transformers package")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Failed to generate answer: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING RAG SYSTEM WITH OLLAMA + HUGGINGFACE")
    print("="*60)
    
    tests = [
        test_ollama_detection,
        test_embeddings,
        test_generation,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
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
        print("\n💡 Tips:")
        print("  - For best performance, install Ollama: https://ollama.ai/download")
        print("  - Then run: ollama pull nomic-embed-text")
        print("  - And: ollama pull llama3.2:3b")
        print("  - The system will work with HuggingFace as fallback")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
