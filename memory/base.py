# Smart Memory v2 - Full A-mem implementation
# Features: rich metatags, temporal decay, weighted graph, composite ranking

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config.settings import (
    DATA_DIR, 
    LIMIT_KEYWORDS_PER_MEMORY,
    LIMIT_KEYWORD_SOURCE_TEXT,
    LIMIT_MEMORY_CANDIDATES
)
from memory.vector_store import get_vector_memory, CHROMA_AVAILABLE
from memory.cache import get_cache


class SmartMemory:
    """
    Full A-mem inspired memory with:
    - Rich metatags (importance, decay, source, success_rate)
    - Temporal decay
    - Weighted relationships
    - Composite ranking for retrieval
    """
    
    DECAY_RATE = 0.98  # Daily decay multiplier
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(DATA_DIR, "agent_memory.json")
        self.memories: List[Dict[str, Any]] = []
        self.vector = get_vector_memory() if CHROMA_AVAILABLE else None
        self._graph = None  # Lazy load
        self._load()
    
    @property
    def graph(self):
        """Lazy load graph to avoid circular imports"""
        if self._graph is None:
            from memory.graph import get_memory_graph
            self._graph = get_memory_graph()
        return self._graph

    def reload(self):
        """Force reload from disk to sync with other processes"""
        self._load()
    
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get("memories", [])
                    # Apply decay on load
                    self._apply_decay()
            except Exception as e:
                print(f"❌ Error loading memory from {self.path}: {e}")
                self.memories = []
    
    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({
                "memories": self.memories,
                "updated": datetime.now().isoformat(),
                "last_decay": datetime.now().isoformat(),  # Track decay time
                "count": len(self.memories)
            }, f, indent=2, ensure_ascii=False)
    
    def _apply_decay(self):
        """Apply temporal decay to all memories"""
        now = datetime.now()
        modified = False
        
        for mem in self.memories:
            created = datetime.fromisoformat(mem.get("created", now.isoformat()))
            days_old = (now - created).days
            
            if days_old > 0:
                # Apply decay based on age
                original_importance = mem.get("base_importance", mem.get("importance", 5))
                decay_factor = self.DECAY_RATE ** days_old
                
                # Also factor in success rate if we have enough data
                success_rate = mem.get("success_rate", 1.0)
                total_uses = mem.get("success_count", 0) + mem.get("fail_count", 0)
                if total_uses >= 3:  # Only adjust if enough data
                    decay_factor *= success_rate  # Low success = faster decay
                
                mem["importance"] = max(1, int(original_importance * decay_factor))
                mem["decay_factor"] = round(decay_factor, 3)
                modified = True
        
        if modified:
            self._save()
    
    def run_decay(self) -> dict:
        """Public method to manually trigger decay (for periodic jobs)"""
        before = sum(m.get("importance", 5) for m in self.memories)
        self._apply_decay()
        after = sum(m.get("importance", 5) for m in self.memories)
        return {
            "memories_processed": len(self.memories),
            "total_importance_before": before,
            "total_importance_after": after,
            "decayed_by": before - after
        }
    
    def add(self, lesson: str, category: str = "general", 
            keywords: List[str] = None, importance: int = 5,
            source_type: str = "system", tools_involved: List[str] = None,
            error_type: str = None) -> Dict:
        """Add memory with rich metatags"""
        
        # Check duplicates
        for m in self.memories[-20:]:
            if m.get("lesson") == lesson:
                m["access_count"] = m.get("access_count", 0) + 1
                m["last_accessed"] = datetime.now().isoformat()
                self._save()
                return m
        
        # Create rich memory entry
        mem_id = len(self.memories)
        entry = {
            # Core
            "id": mem_id,
            "lesson": lesson,
            "category": category,
            "keywords": keywords or self._extract_keywords(lesson),
            
            # Metatags
            "importance": importance,
            "base_importance": importance,  # Original before decay
            "access_count": 0,
            "success_count": 0,  # Times this helped
            "fail_count": 0,     # Times this didn't help
            "success_rate": 1.0,
            
            # Source
            "source_type": source_type,  # refinement, error, user, tool
            "tools_involved": tools_involved or [],
            "error_type": error_type,
            
            # Timestamps
            "created": datetime.now().isoformat(),
            "last_accessed": None,
            "decay_factor": 1.0,
            
            # Graph links (stored here for reference)
            "links": []
        }
        
        # Find and create weighted links
        self._create_links(entry)
        
        self.memories.append(entry)
        self._save()
        
        # Add to graph
        self.graph.add_memory_node(mem_id, {
            "category": category,
            "importance": importance
        })
        
        # Add to vector store
        if self.vector and CHROMA_AVAILABLE:
            self.vector.add(lesson, {"category": category, "id": mem_id})
        
        print(f"  💡 Learned: {lesson[:50]}... [imp:{importance}, links:{len(entry['links'])}]")
        return entry
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract semantic keywords using LLM for better quality"""
        try:
            from core.llm_client import LLMClient
            from config.settings import MEMORY_SLOT
            llm = LLMClient()
            
            prompt = f"""Extract 3-10 semantic keywords from this lesson. Output ONLY comma-separated keywords, nothing else.

LESSON: {text[:LIMIT_KEYWORD_SOURCE_TEXT]}

KEYWORDS:"""
            
            response = llm.generate(prompt, temp=0.2, slot_id=MEMORY_SLOT)
            # Parse comma-separated keywords
            keywords = [k.strip().lower() for k in response.split(',') if k.strip()]
            return keywords[:LIMIT_KEYWORDS_PER_MEMORY] if keywords else self._fallback_keywords(text)
        except:
            return self._fallback_keywords(text)
    
    def _fallback_keywords(self, text: str) -> List[str]:
        """Fallback heuristic keywords if LLM fails"""
        clean_text = text.lower().replace('*', '').replace('#', '').replace('`', '')
        words = clean_text.split()
        stop_words = {"when", "always", "should", "must", "that", "this", "with", "from", "the", "and", "for"}
        return [w.strip('.,;:()[]') for w in words if len(w) > 4 and w not in stop_words][:LIMIT_KEYWORDS_PER_MEMORY]
    
    def _create_links(self, new_entry: Dict) -> None:
        """Create weighted links to related memories"""
        new_id = new_entry["id"]
        new_words = set(new_entry["lesson"].lower().split())
        new_category = new_entry["category"]
        
        for mem in self.memories[-15:]:
            if "id" not in mem:
                continue
                
            if mem["id"] == new_id:
                continue
            
            old_words = set(mem.get("lesson", "").lower().split())
            
            # Calculate similarity weight
            overlap = len(new_words & old_words)
            same_category = new_category == mem.get("category")
            same_tools = bool(set(new_entry.get("tools_involved", [])) & 
                            set(mem.get("tools_involved", [])))
            
            # Weight calculation
            weight = 0.0
            if overlap >= 3:
                weight += 0.3 + (overlap * 0.05)
            if same_category:
                weight += 0.2
            if same_tools:
                weight += 0.3
            
            # Add link if significant
            if weight >= 0.3:
                weight = min(1.0, weight)
                new_entry["links"].append({
                    "to": mem["id"],
                    "weight": round(weight, 2),
                    "type": "similar" if overlap > 5 else "related"
                })
                # Add to graph
                self.graph.add_link(new_id, mem["id"], weight)
    
    def get_relevant(self, query: str, n: int = 3) -> str:
        """Get relevant memories using composite ranking with caching"""
        
        if not self.memories:
            return ""
        
        # Check cache first
        cache = get_cache()
        cached = cache.get(query)
        if cached:
            return cached
        
        # Get candidates
        candidates = self._get_candidates(query)
        
        if not candidates:
            return ""
        
        # Composite ranking
        ranked = self._rank_candidates(candidates, query)
        
        # Take top n
        top = ranked[:n]
        
        # Update access counts
        for mem, _ in top:
            mem["access_count"] = mem.get("access_count", 0) + 1
            mem["last_accessed"] = datetime.now().isoformat()
        self._save()
        
        # Format output
        lines = ["RELEVANT LESSONS:"]
        for mem, score in top:
            lines.append(f"- {mem['lesson'][:100]}")
        
        result = "\n".join(lines)
        
        # Save to cache for future queries
        cache.set(query, result)
        
        return result
    
    def _get_candidates(self, query: str) -> List[Dict]:
        """Get candidate memories for ranking"""
        candidates = []
        
        # Vector search if available
        if self.vector and CHROMA_AVAILABLE:
            results = self.vector.search(query, n_results=10)
            for text in results:
                for mem in self.memories:
                    if text[:50] in mem.get("lesson", ""):
                        candidates.append(mem)
                        break
        
        # Also include recent high-importance memories
        for mem in self.memories[-10:]:
            if mem not in candidates and mem.get("importance", 0) >= 5:
                candidates.append(mem)
        
        return candidates[:LIMIT_MEMORY_CANDIDATES]  # Max candidates from settings
    
    def _rank_candidates(self, candidates: List[Dict], query: str) -> List[tuple]:
        """Rank candidates using composite score + PageRank centrality"""
        query_words = set(query.lower().split())
        scored = []
        
        # Get PageRank scores from graph
        pagerank_scores = {}
        try:
            central = self.graph.get_central_memories(top_k=20)
            pagerank_scores = {mem_id: pr_score for mem_id, pr_score in central}
        except:
            pass  # Graph might be empty
        
        for mem in candidates:
            # Semantic overlap
            lesson_words = set(mem.get("lesson", "").lower().split())
            overlap = len(query_words & lesson_words)
            semantic_score = min(1.0, overlap * 0.15)
            
            # Importance (normalized)
            importance_score = mem.get("importance", 5) / 10
            
            # Access frequency (log scale)
            access = mem.get("access_count", 0)
            access_score = min(1.0, (access + 1) ** 0.3 / 3)
            
            # Decay (already applied)
            decay_score = mem.get("decay_factor", 1.0)
            
            # Success rate
            success_score = mem.get("success_rate", 0.5)
            
            # NEW: PageRank centrality (how connected is this memory?)
            mem_id = mem.get("id")
            centrality_score = pagerank_scores.get(mem_id, 0.0) * 10  # Scale up for visibility
            
            # Composite score with weights
            final_score = (
                semantic_score * 0.30 +
                importance_score * 0.20 +
                access_score * 0.10 +
                decay_score * 0.10 +
                success_score * 0.15 +
                centrality_score * 0.15  # NEW: PageRank weight
            )
            
            scored.append((mem, final_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def mark_success(self, memory_id: int) -> None:
        """Mark a memory as successful (it helped)"""
        for mem in self.memories:
            if mem.get("id") == memory_id:
                mem["success_count"] = mem.get("success_count", 0) + 1
                total = mem["success_count"] + mem.get("fail_count", 0)
                mem["success_rate"] = mem["success_count"] / total if total > 0 else 0.5
                # Boost importance slightly
                mem["importance"] = min(10, mem.get("importance", 5) + 1)
                self._save()
                break
    
    def mark_failure(self, memory_id: int) -> None:
        """Mark a memory as unsuccessful"""
        for mem in self.memories:
            if mem.get("id") == memory_id:
                mem["fail_count"] = mem.get("fail_count", 0) + 1
                total = mem.get("success_count", 0) + mem["fail_count"]
                mem["success_rate"] = mem.get("success_count", 0) / total if total > 0 else 0.5
                # Decrease importance slightly
                mem["importance"] = max(1, mem.get("importance", 5) - 1)
                self._save()
                break
    
    def clear(self):
        self.memories = []
        self._save()
        
        # Also clear the graph to keep in sync
        try:
            graph = self.graph
            graph.graph.clear()  # NetworkX graph clear
            graph._save()
            print("🧹 Memory and graph cleared")
        except Exception as e:
            print(f"🧹 Memory cleared (graph sync failed: {e})")
    
    def stats(self) -> Dict:
        total = len(self.memories)
        with_links = sum(1 for m in self.memories if m.get("links"))
        avg_importance = sum(m.get("importance", 5) for m in self.memories) / total if total else 0
        
        return {
            "total": total,
            "with_links": with_links,
            "avg_importance": round(avg_importance, 1),
            "graph": self.graph.stats(),
            "vector_available": CHROMA_AVAILABLE
        }
    
    # Backwards compatibility
    def get_relevant_context(self, query: str) -> str:
        return self.get_relevant(query)
    
    def add_lesson(self, lesson: str, category: str = "general", keywords: List[str] = None):
        return self.add(lesson, category, keywords)


import threading

# Alias
AgentMemory = SmartMemory

# Global instance
_memory: Optional[SmartMemory] = None
_mem_lock = threading.Lock()

def get_memory() -> SmartMemory:
    global _memory
    if _memory is None:
        with _mem_lock:
            if _memory is None:
                _memory = SmartMemory()
    return _memory
