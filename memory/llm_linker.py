# LLM-Linker - Intelligent memory linking using LLM
# Finds semantic connections between memories

from typing import List, Dict, Optional, Tuple
from core.llm_client import LLMClient
from config.settings import MEMORY_SLOT, LLM_RANKING_THRESHOLD
from memory.base import get_memory


class LLMLinker:
    """
    Uses LLM to find relevant memories and create intelligent links.
    Called at query time and during refinement.
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.memory = get_memory()
    
    def search_relevant(self, query: str, category: str = None, 
                        context: Dict = None, top_k: int = 3) -> List[Dict]:
        """
        Search for relevant memories using LLM understanding.
        
        Args:
            query: User query or current task
            category: Optional category filter (file_create, code_exec, etc.)
            context: Optional extra context (errors, tool results, etc.)
            top_k: Max number of memories to return
        """
        # Get candidate memories
        candidates = self._get_candidates(query, category)
        
        if not candidates:
            return []
        
        # OPTIMIZATION 3: Use heuristic ranking for small memory sets (saves LLM call)
        # Only use LLM ranking when we have many candidates to choose from
        
        if len(candidates) <= top_k:
            return candidates
        
        if len(candidates) <= LLM_RANKING_THRESHOLD:
            # Heuristic ranking: by importance and recency
            ranked = sorted(candidates, key=lambda m: (
                m.get("importance", 5),  # Higher importance first
                m.get("access_count", 0),  # More accessed first
                -m.get("id", 0)  # More recent first (higher ID = newer)
            ), reverse=True)
            print(f"    📊 Heuristic ranking ({len(candidates)} candidates)")
            return ranked[:top_k]
        
        # Use LLM only for large candidate sets
        print(f"    🤖 LLM ranking ({len(candidates)} candidates)")
        ranked = self._llm_rank(query, candidates, context)
        
        return ranked[:top_k]
    
    def _get_candidates(self, query: str, category: str = None) -> List[Dict]:
        """Get candidate memories for LLM ranking"""
        all_mems = self.memory.memories[-20:]  # Recent memories
        
        if not category:
            return all_mems
        
        # Filter by category
        filtered = [m for m in all_mems if m.get("category") == category]
        
        # If too few, include general too
        if len(filtered) < 3:
            general = [m for m in all_mems if m.get("category") == "general"]
            filtered.extend(general[:5])
        
        return filtered
    
    def _llm_rank(self, query: str, candidates: List[Dict], 
                  context: Dict = None) -> List[Dict]:
        """Use LLM to rank memory relevance"""
        
        # Build context string
        ctx_str = ""
        if context:
            if context.get("errors"):
                ctx_str += f"Errors: {context['errors']}\n"
            if context.get("tools_tried"):
                ctx_str += f"Tools tried: {context['tools_tried']}\n"
        
        # Format candidates
        cand_str = "\n".join([
            f"{i+1}. [{m.get('category', 'general')}] {m.get('lesson', '')[:80]}"
            for i, m in enumerate(candidates[:10])
        ])
        
        prompt = f"""Given this task, rank which lessons are most relevant (1=most relevant):

TASK: {query}
{ctx_str}

LESSONS:
{cand_str}

Return ONLY the numbers of the 3 most relevant, e.g: 2,5,1
RANKING:"""

        response = self.llm.generate(prompt, temp=0.3, slot_id=MEMORY_SLOT)
        
        # Parse ranking
        return self._parse_ranking(response, candidates)
    
    def _parse_ranking(self, response: str, candidates: List[Dict]) -> List[Dict]:
        """Parse LLM ranking response"""
        ranked = []
        
        # Extract numbers from response
        import re
        numbers = re.findall(r'\d+', response)
        
        for num_str in numbers[:5]:
            idx = int(num_str) - 1
            if 0 <= idx < len(candidates):
                mem = candidates[idx]
                if mem not in ranked:
                    ranked.append(mem)
        
        return ranked
    
    def create_link(self, new_memory: Dict, existing_memories: List[Dict]) -> List[Dict]:
        """
        Use LLM to determine links between new and existing memories.
        Returns list of links with weights.
        """
        if not existing_memories:
            return []
        
        new_text = new_memory.get("lesson", "")
        
        # Format existing memories
        existing_str = "\n".join([
            f"{m['id']}. {m.get('lesson', '')[:60]}"
            for m in existing_memories[:8]
        ])
        
        prompt = f"""Analyze connections between new memory and existing ones:

NEW: {new_text}

EXISTING:
{existing_str}

Which existing memories are related? For each, rate connection 1-10.
Format: ID:SCORE (e.g., 3:8, 5:6)
Only include connections score 5+.

CONNECTIONS:"""

        response = self.llm.generate(prompt, temp=0.3, slot_id=MEMORY_SLOT)
        
        return self._parse_links(response, existing_memories)
    
    def _parse_links(self, response: str, candidates: List[Dict]) -> List[Dict]:
        """Parse LLM link response"""
        links = []
        
        import re
        matches = re.findall(r'(\d+):(\d+)', response)
        
        for id_str, score_str in matches:
            mem_id = int(id_str)
            score = int(score_str)
            
            # Find memory with this ID
            for mem in candidates:
                if mem.get("id") == mem_id and score >= 5:
                    links.append({
                        "to": mem_id,
                        "weight": min(1.0, score / 10),
                        "type": "llm_linked"
                    })
                    break
        
        return links


# Global instance
_llm_linker: Optional[LLMLinker] = None

def get_llm_linker() -> LLMLinker:
    global _llm_linker
    if _llm_linker is None:
        _llm_linker = LLMLinker()
    return _llm_linker
