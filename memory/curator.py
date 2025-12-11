# Memory Curator Agent - Background process for memory curation
# Runs periodically to curate memories and update tool schemas

import threading
import time
import re
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime

from config.settings import DATA_DIR


class MemoryCuratorAgent:
    """
    Background agent that curates memory and tool schemas.
    
    Tasks:
    1. Curate memories (merge near-duplicates)
    2. Update tool error_hints from error patterns
    3. Strengthen/weaken graph links based on co-access
    4. Clean low-decay memories
    
    Runs in a background thread, non-blocking.
    """
    
    def __init__(self, interval_iterations: int = 5):
        self.interval = interval_iterations
        self.iteration_count = 0
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Error pattern tracking
        self._error_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # Format: {tool_name: {error_type: count}}
        
        # Curation stats
        self.stats = {
            "curations_run": 0,
            "memories_merged": 0,
            "hints_added": 0,
            "links_updated": 0,
            "last_run": None
        }
    
    def record_error(self, tool_name: str, error_type: str, error_message: str = ""):
        """
        Record an error for pattern learning.
        Called by executor/verifier when tools fail.
        """
        with self._lock:
            self._error_patterns[tool_name][error_type] += 1
    
    def record_success_lesson(self, tool_name: str, error_type: str, lesson: str):
        """
        Record a lesson that fixed an error.
        Called when agent successfully fixes an error.
        """
        with self._lock:
            # Store lesson for potential hint update
            key = f"{tool_name}:{error_type}"
            if not hasattr(self, '_learned_hints'):
                self._learned_hints: Dict[str, str] = {}
            if key not in self._learned_hints:
                self._learned_hints[key] = lesson[:100]  # Truncate
    
    def get_top_errors(self, n: int = 5) -> List[Dict]:
        """
        Get top N most frequent errors for task generation.
        Used by task generator to create targeted practice tasks.
        
        Returns:
            List of dicts: [{"tool": "python_exec", "error": "IndexError", "count": 5}, ...]
        """
        with self._lock:
            all_errors = []
            for tool_name, errors in self._error_patterns.items():
                for error_type, count in errors.items():
                    if count >= 2:  # Only if happened 2+ times
                        all_errors.append({
                            "tool": tool_name,
                            "error": error_type,
                            "count": count
                        })
            
            # Sort by count descending
            all_errors.sort(key=lambda x: x["count"], reverse=True)
            return all_errors[:n]
    
    def get_error_summary_for_prompt(self) -> str:
        """
        Get formatted error summary for task generator prompt.
        
        Returns:
            String formatted for prompt injection
        """
        top_errors = self.get_top_errors(5)
        if not top_errors:
            return ""
        
        lines = ["## FREQUENT ERRORS (practice these areas):"]
        for err in top_errors:
            lines.append(f"- {err['error']} in {err['tool']} ({err['count']} times)")
        
        return "\n".join(lines)
    
    def tick(self):
        """
        Called after each iteration of autonomous loop.
        Triggers curation every N iterations.
        """
        self.iteration_count += 1
        
        if self.iteration_count % self.interval == 0:
            self._run_curation_async()
    
    def _run_curation_async(self):
        """Run curation in background thread"""
        if self._thread and self._thread.is_alive():
            return  # Already running
        
        self._thread = threading.Thread(target=self._curate, daemon=True)
        self._thread.start()
    
    def _curate(self):
        """Main curation logic - runs in background"""
        try:
            print(f"\n🔧 MemoryCurator: Starting curation...")
            start = time.time()
            
            # 1. Update tool error hints from learned patterns
            hints_added = self._update_error_hints()
            
            # 2. Curate memories (merge near-duplicates)
            merged = self._merge_duplicate_memories()
            
            # 3. Update memory graph links
            links_updated = self._update_graph_links()
            
            # 4. Clean low-decay memories
            cleaned = self._clean_low_decay_memories()
            
            # Update stats
            self.stats["curations_run"] += 1
            self.stats["hints_added"] += hints_added
            self.stats["memories_merged"] += merged
            self.stats["links_updated"] += links_updated
            self.stats["last_run"] = datetime.now().isoformat()
            
            duration = time.time() - start
            print(f"🔧 MemoryCurator: Done in {duration:.1f}s "
                  f"(hints:{hints_added}, merged:{merged}, links:{links_updated})")
            
        except Exception as e:
            print(f"⚠️ MemoryCurator error: {e}")
    
    def _update_error_hints(self) -> int:
        """Update tool schemas with learned error hints"""
        from tools.schema_loader import get_schema_loader
        
        loader = get_schema_loader()
        hints_added = 0
        
        with self._lock:
            learned = getattr(self, '_learned_hints', {})
            
            for key, hint in list(learned.items()):
                try:
                    tool_name, error_type = key.split(":", 1)
                    if loader.add_error_hint(tool_name, error_type, hint):
                        hints_added += 1
                        print(f"  📝 Added hint: {tool_name}:{error_type}")
                except Exception as e:
                    pass
            
            # Clear learned hints after processing
            if hasattr(self, '_learned_hints'):
                self._learned_hints.clear()
        
        return hints_added
    
    def _merge_duplicate_memories(self) -> int:
        """
        Merge near-duplicate memories using heuristic (NO LLM).
        
        Uses word overlap to detect duplicates. Avoids LLM calls in background
        which would conflict with worker slots.
        """
        try:
            from memory.base import get_memory
            
            memory = get_memory()
            recent = memory.get_recent(limit=20)
            merged = 0
            
            # Simple heuristic: word overlap > 50%
            seen_words = {}  # {frozenset(words): memory_id}
            
            for mem in recent:
                lesson = mem.get("lesson", "")
                if not lesson:
                    continue
                
                # Extract significant words (>3 chars)
                words = set(w.lower() for w in lesson.split() if len(w) > 3)
                if len(words) < 3:
                    continue
                
                # Check overlap with seen memories
                for seen_key, seen_id in list(seen_words.items()):
                    overlap = len(words & seen_key) / max(len(words), len(seen_key))
                    if overlap > 0.5:
                        # Potential duplicate - just count, don't merge yet
                        merged += 1
                        break
                else:
                    # New unique memory
                    seen_words[frozenset(words)] = mem.get("id", 0)
            
            return merged
        except Exception as e:
            return 0
    
    def _update_graph_links(self) -> int:
        """Strengthen/weaken links based on co-access patterns"""
        try:
            from memory.graph import get_memory_graph
            
            graph = get_memory_graph()
            
            # Apply decay to all links
            decayed = graph.apply_decay(factor=0.99)
            
            return decayed
        except Exception as e:
            return 0
    
    def _clean_low_decay_memories(self) -> int:
        """Remove memories with very low importance/decay"""
        try:
            from memory.base import get_memory
            
            memory = get_memory()
            
            # Get all memories and find low-value ones
            all_mems = memory.get_all()
            cleaned = 0
            
            for mem in all_mems:
                importance = mem.get("importance", 5)
                access_count = mem.get("access_count", 0)
                
                # Only clean if very low value AND old
                if importance <= 2 and access_count == 0:
                    # Don't actually delete for now, just log
                    # memory.delete(mem["id"])
                    cleaned += 1
            
            return cleaned
        except Exception as e:
            return 0
    
    def force_curate(self):
        """Force immediate curation (for testing)"""
        self._curate()
    
    def get_stats(self) -> Dict:
        """Get curation statistics"""
        return self.stats.copy()


# Global instance
_curator: Optional[MemoryCuratorAgent] = None


def get_curator() -> MemoryCuratorAgent:
    """Get or create global curator"""
    global _curator
    if _curator is None:
        _curator = MemoryCuratorAgent()
    return _curator


def record_tool_error(tool_name: str, error_type: str, message: str = ""):
    """Convenience function to record tool errors"""
    get_curator().record_error(tool_name, error_type, message)


def record_error_fix(tool_name: str, error_type: str, lesson: str):
    """Convenience function to record successful error fixes"""
    get_curator().record_success_lesson(tool_name, error_type, lesson)


def tick_curator():
    """Convenience function to tick the curator"""
    get_curator().tick()
