# Memory Linker - Intelligent connections between memories
# Inspired by A-mem's Zettelkasten approach

from typing import List, Dict, Optional
from core.llm_client import LLMClient
from memory.vector_store import get_vector_memory, CHROMA_AVAILABLE


class MemoryLinker:
    """
    Creates intelligent links between memories.
    When adding new memory, finds related ones and creates connections.
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.vector = get_vector_memory() if CHROMA_AVAILABLE else None
    
    def find_related(self, new_memory: str, top_k: int = 3) -> List[Dict]:
        """Find memories related to the new one using vector search"""
        if not self.vector or not CHROMA_AVAILABLE:
            return []
        
        # Search for similar memories
        similar = self.vector.search(new_memory, n_results=top_k)
        
        return [{"text": mem, "similarity": "high"} for mem in similar]
    
    def analyze_connections(self, new_memory: str, related: List[Dict]) -> Dict:
        """
        Use LLM to analyze connections between new and existing memories.
        Returns which memories should be linked and how.
        """
        if not related:
            return {"links": [], "should_update": []}
        
        related_text = "\n".join([f"- {r['text'][:100]}" for r in related])
        
        prompt = f"""Analyze memory connections:

NEW MEMORY: {new_memory}

EXISTING MEMORIES:
{related_text}

Which existing memories are related? Answer JSON:
{{"links": ["memory1", "memory2"], "reason": "why related"}}

Keep it brief. If no strong connection, return empty links."""

        response = self.llm.generate(prompt, temp=0.3)
        
        # Parse response (simple extraction)
        return self._parse_links(response, related)
    
    def _parse_links(self, response: str, related: List[Dict]) -> Dict:
        """Extract links from LLM response"""
        # Simple: if LLM mentions any related memory, link it
        links = []
        for r in related:
            # Check if any words from the memory appear in response
            words = set(r['text'].lower().split()[:5])
            if any(w in response.lower() for w in words if len(w) > 4):
                links.append(r['text'])
        
        return {
            "links": links[:2],  # Max 2 links
            "should_update": []  # For now, no updates
        }


def get_linker() -> MemoryLinker:
    return MemoryLinker()
