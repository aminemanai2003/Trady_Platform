"""
Base agent class for LangChain-based trading agents
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import time

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from core.llm_factory import LLMFactory
from agents.models import AgentSignal


@dataclass
class AgentOutput:
    """Standardized agent output"""
    signal: str  # BUY, SELL, NEUTRAL
    confidence: float  # 0 to 1
    reasoning: str
    features_used: Dict


class BaseAgent(ABC):
    """Base class for all trading agents"""
    
    AGENT_TYPE = None  # Override in subclasses
    
    def __init__(self):
        self.llm = LLMFactory.get_llm()
        self.decision_chain = self._create_decision_chain()
    
    @abstractmethod
    def _create_decision_chain(self) -> LLMChain:
        """Create LangChain decision chain"""
        pass
    
    @abstractmethod
    def _fetch_features(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict:
        """Fetch relevant features for decision making"""
        pass
    
    def analyze(self, symbol: str, timestamp: Optional[datetime] = None) -> AgentOutput:
        """Main analysis method"""
        
        start_time = time.time()
        
        # Fetch features
        features = self._fetch_features(symbol, timestamp)
        
        # Make decision using LLM
        decision_result = self._make_decision(features)
        
        # Track latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Save signal to database
        self._save_signal(symbol, decision_result, features, latency_ms)
        
        return decision_result
    
    @abstractmethod
    def _make_decision(self, features: Dict) -> AgentOutput:
        """Make trading decision based on features"""
        pass
    
    def _save_signal(self, symbol: str, output: AgentOutput, 
                    features: Dict, latency_ms: int):
        """Save agent signal to database"""
        
        AgentSignal.objects.create(
            agent_type=self.AGENT_TYPE,
            symbol=symbol,
            signal=output.signal,
            confidence=output.confidence,
            reasoning=output.reasoning,
            features_used=features,
            latency_ms=latency_ms
        )
    
    def _parse_llm_decision(self, llm_output: str) -> tuple:
        """
        Parse LLM output to extract signal and confidence
        Expected format:
        Signal: BUY/SELL/NEUTRAL
        Confidence: 0.0-1.0
        """
        signal = "NEUTRAL"
        confidence = 0.5
        
        # Extract signal
        if "BUY" in llm_output.upper():
            signal = "BUY"
        elif "SELL" in llm_output.upper():
            signal = "SELL"
        
        # Extract confidence
        import re
        confidence_match = re.search(r'Confidence:\s*([0-9.]+)', llm_output)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                confidence = max(0.0, min(1.0, confidence))
            except:
                pass
        
        return signal, confidence
