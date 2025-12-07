# Memory Evolution - Updates old memories based on new info
# Inspired by A-mem's memory evolution concept

from typing import List, Dict, Optional
from datetime import datetime
from core.llm_client import LLMClient


class MemoryEvolution:
    """
    Handles memory evolution: updating old memories when new related info arrives.
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    def should_evolve(self, new_memory: str, old_memory: Dict) -> bool:
        """Determine if old memory should be updated based on new info"""
        # Simple heuristics:
        # 1. Same category
        # 2. Contradictory info
        # 3. More specific version
        
        old_text = old_memory.get("lesson", "")
        
        # Check for contradiction keywords
        contradiction_words = ["instead", "actually", "wrong", "correct", "fix"]
        has_contradiction = any(w in new_memory.lower() for w in contradiction_words)
        
        # Check for same topic (word overlap)
        new_words = set(new_memory.lower().split())
        old_words = set(old_text.lower().split())
        overlap = len(new_words & old_words)
        
        return has_contradiction or overlap > 5
    
    def evolve_memory(self, old_memory: Dict, new_memory: str) -> Dict:
        """
        Evolve an old memory by merging with new info.
        Returns updated memory dict.
        """
        old_text = old_memory.get("lesson", "")
        
        # Use LLM to merge memories
        prompt = f"""Merge these two related memories into one improved version:

OLD: {old_text}
NEW: {new_memory}

Write a single, improved lesson that combines both.
Be concise (1-2 sentences max).

MERGED:"""

        merged = self.llm.generate(prompt, temp=0.3)
        
        # Clean up response
        merged = merged.strip()
        if merged.startswith("MERGED:"):
            merged = merged[7:].strip()
        
        return {
            "lesson": merged[:200],  # Max length
            "category": old_memory.get("category", "general"),
            "keywords": old_memory.get("keywords", []),
            "time": datetime.now().isoformat(),
            "evolved_from": old_text[:50],
            "evolution_count": old_memory.get("evolution_count", 0) + 1
        }
    
    def get_evolution_candidates(self, new_memory: str, all_memories: List[Dict]) -> List[Dict]:
        """Find which memories should be evolved"""
        candidates = []
        for mem in all_memories[-20:]:  # Check recent memories only
            if self.should_evolve(new_memory, mem):
                candidates.append(mem)
        return candidates[:2]  # Max 2 evolutions per new memory


def get_evolution() -> MemoryEvolution:
    return MemoryEvolution()
