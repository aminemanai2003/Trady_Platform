"""
Free LLM factory for agent reasoning
Uses local/free models only
"""
from langchain_community.llms import HuggingFacePipeline
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch


class LLMFactory:
    """Factory for creating free LLM instances"""
    
    _llm_cache = None
    _embeddings_cache = None
    
    @classmethod
    def get_llm(cls, model_name: str = "google/flan-t5-base"):
        """
        Get a free LLM instance
        Default: FLAN-T5 (good for reasoning tasks)
        Alternatives: 
        - "mistralai/Mistral-7B-Instruct-v0.2" (if GPU available)
        - "google/flan-t5-large"
        """
        if cls._llm_cache is not None:
            return cls._llm_cache
        
        # Use smaller models for CPU inference
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            low_cpu_mem_usage=True
        )
        
        pipe = pipeline(
            "text2text-generation" if "t5" in model_name.lower() else "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=False
        )
        
        cls._llm_cache = HuggingFacePipeline(pipeline=pipe)
        return cls._llm_cache
    
    @classmethod
    def get_embeddings(cls, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Get free embedding model
        Default: all-MiniLM-L6-v2 (384 dim, fast, good quality)
        """
        if cls._embeddings_cache is not None:
            return cls._embeddings_cache
        
        cls._embeddings_cache = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        return cls._embeddings_cache
