# Memory Evolution - Updates old memories based on new info
# Inspired by A-mem's memory evolution concept

from typing import List, Dict, Optional
from datetime import datetime
from core.llm_client import LLMClient
from config.settings import MEMORY_SLOT


class MemoryEvolution:
    """
    Handles memory evolution: updating old memories when new related info arrives.
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    def should_evolve(self, new_memory: str, old_memory: Dict) -> bool:
        """Use LLM to determine if memories are related and should evolve"""
        old_text = old_memory.get("lesson", "")
        
        # Quick heuristic pre-check (avoid LLM call if clearly unrelated)
        new_words = set(new_memory.lower().split())
        old_words = set(old_text.lower().split())
        overlap = len(new_words & old_words)
        
        if overlap < 3:  # Too different, skip LLM
            return False
        
        # Use LLM for semantic check
        try:
            prompt = f"""Are these two lessons about the SAME topic and should be merged?
OLD: {old_text[:200]}
NEW: {new_memory[:200]}

Answer ONLY: YES or NO"""
            response = self.llm.generate(prompt, temp=0.1, slot_id=MEMORY_SLOT)
            return "YES" in response.upper()
        except:
            return overlap > 5  # Fallback to heuristic
    
    def evolve_memory(self, old_memory: Dict, new_memory: str) -> Dict:
        """
        Evolve memory with LLM-based contradiction detection.
        Either MERGE (combine info) or REPLACE (if contradicts).
        """
        old_text = old_memory.get("lesson", "")
        
        # First, detect if there's a contradiction
        try:
            detect_prompt = f"""Do these lessons CONTRADICT each other?
OLD: {old_text}
NEW: {new_memory}

Answer: CONTRADICT or COMPATIBLE"""
            detect_response = self.llm.generate(detect_prompt, temp=0.1, slot_id=MEMORY_SLOT)
            is_contradiction = "CONTRADICT" in detect_response.upper()
        except:
            is_contradiction = False
        
        if is_contradiction:
            # If contradiction, NEW wins (more recent = more correct)
            return {
                "lesson": new_memory.strip(),
                "category": old_memory.get("category", "general"),
                "keywords": old_memory.get("keywords", []),
                "time": datetime.now().isoformat(),
                "evolved_from": f"[REPLACED] {old_text[:30]}...",
                "evolution_count": old_memory.get("evolution_count", 0) + 1
            }
        
        # Otherwise, merge them intelligently
        merge_prompt = f"""Merge these two related lessons into ONE concise rule.
Keep the most specific and actionable information.

OLD: {old_text}
NEW: {new_memory}

MERGED (1-2 sentences only):"""

        merged = self.llm.generate(merge_prompt, temp=0.3, slot_id=MEMORY_SLOT)
        merged = merged.strip()
        if merged.startswith("MERGED"):
            merged = merged.split(":", 1)[-1].strip()
        
        return {
            "lesson": merged,
            "category": old_memory.get("category", "general"),
            "keywords": old_memory.get("keywords", []),
            "time": datetime.now().isoformat(),
            "evolved_from": f"[MERGED] {old_text[:30]}...",
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
