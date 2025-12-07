# Memory Orchestrator - Unified interface for all memory systems
# Coordinates: Context Vectors + LLM-Linker + SmartMemory + ICV

from dataclasses import dataclass
from typing import List, Dict, Optional
from memory.base import get_memory, SmartMemory
from memory.context_vectors import get_context_vectors, get_icv, ContextVectors, InContextVector
from memory.llm_linker import get_llm_linker, LLMLinker
from memory.graph import get_memory_graph
from memory.working_memory import get_working_memory, WorkingMemory


@dataclass
class MemoryContext:
    """Complete memory context for workers/refiner"""
    memories: List[Dict]       # Relevant memories
    category: str              # Detected category
    tools_suggested: List[str] # Tools likely needed
    tips: str                  # ICV tips
    project_files: List[Dict] = None # Relevant project files (new)
    
    def to_prompt(self) -> str:
        """Convert to prompt string for LLM"""
        parts = []
        
        # Memory lessons
        if self.memories:
            lessons = "\n".join([f"- {m.get('lesson', '')[:100]}" for m in self.memories])
            parts.append(f"RELEVANT LESSONS:\n{lessons}")
        
        # Category and tools
        if self.tools_suggested:
            parts.append(f"TASK TYPE: {self.category}")
            parts.append(f"SUGGESTED TOOLS: {', '.join(self.tools_suggested)}")
        
        # ICV tips
        if self.tips:
            parts.append(self.tips)

        # Project context
        if self.project_files:
            files_str = "\n".join([f"- {f['path']}: {f['content'][:200]}..." for f in self.project_files])
            parts.append(f"PROJECT CONTEXT (Relevant Files):\n{files_str}")
        
        return "\n\n".join(parts) if parts else ""


class MemoryOrchestrator:
    """
    Unified memory interface that coordinates all memory subsystems.
    Single point of contact for workers and refiner.
    """
    
    def __init__(self):
        self.memory: SmartMemory = get_memory()
        self.context_vectors: ContextVectors = get_context_vectors()
        self.icv: InContextVector = get_icv()
        self.linker: LLMLinker = get_llm_linker()
        self.graph = get_memory_graph()
        self.working_memory: WorkingMemory = get_working_memory()
    
    def get_context(self, query: str, use_llm: bool = True) -> MemoryContext:
        """
        Get complete memory context for a query.
        Called at start of Poetiq run.
        """
        # 1. Detect category using Context Vectors
        category, confidence = self.context_vectors.detect_category(query)
        
        # 2. Get suggested tools
        tools = self.context_vectors.get_relevant_tools(query)
        
        # 3. Get ICV tips for category
        tips = self.icv.get_icv(category)
        
        # 4. Get relevant memories (LLM or heuristic)
        if use_llm and len(self.memory.memories) > 5:
            memories = self.linker.search_relevant(query, category)
        else:
            # Fallback to heuristic search
            memories = self._heuristic_search(query, category)
        
        # 5. Get project context (NEW)
        project_files = self.working_memory.search_project(query)
        
        return MemoryContext(
            memories=memories,
            category=category,
            tools_suggested=tools,
            tips=tips,
            project_files=project_files
        )
    
    def get_refine_context(self, query: str, current_response: str,
                          errors: List[str] = None, 
                          tools_tried: List[str] = None) -> MemoryContext:
        """
        Get memory context during refinement.
        Uses error/response info to find more relevant memories.
        """
        # Build context for smarter search
        context = {
            "errors": errors,
            "tools_tried": tools_tried,
            "response_snippet": current_response[:200]
        }
        
        # Use LLM linker with extra context
        memories = self.linker.search_relevant(
            query, 
            context=context
        )
        
        # Re-detect category (might have changed based on errors)
        category, _ = self.context_vectors.detect_category(query)
        tools = self.context_vectors.get_relevant_tools(query)
        tips = self.icv.get_icv(category)
        
        # Get project context
        project_files = self.working_memory.search_project(query)
        
        return MemoryContext(
            memories=memories,
            category=category,
            tools_suggested=tools,
            tips=tips,
            project_files=project_files
        )
    
    def _heuristic_search(self, query: str, category: str) -> List[Dict]:
        """Fallback heuristic search without LLM"""
        # Use SmartMemory's built-in search
        result = self.memory.get_relevant(query, n=3)
        
        # Convert back to memory dicts
        memories = []
        if result:
            for line in result.split('\n')[1:]:  # Skip header
                line = line.strip().lstrip('- ')
                for mem in self.memory.memories:
                    if line[:50] in mem.get("lesson", ""):
                        memories.append(mem)
                        break
        
        return memories[:3]
    
    def learn(self, lesson: str, category: str = None, 
              tools: List[str] = None, error_type: str = None,
              use_llm_linking: bool = True) -> Dict:
        """
        Add a new memory with intelligent linking.
        Called by MemoryLearner at end of session.
        """
        # Detect category if not provided
        if not category:
            category, _ = self.context_vectors.detect_category(lesson)
        
        # Add memory with basic metadata
        entry = self.memory.add(
            lesson=lesson,
            category=category,
            tools_involved=tools or [],
            error_type=error_type
        )
        
        # Use LLM to create intelligent links
        if use_llm_linking and len(self.memory.memories) > 3:
            existing = self.memory.memories[-15:-1]  # Recent except this one
            llm_links = self.linker.create_link(entry, existing)
            
            # Add links to graph
            for link in llm_links:
                self.graph.add_link(entry["id"], link["to"], link["weight"], "llm")
            
            # Update entry with links
            entry["links"].extend(llm_links)
            self.memory._save()
        
        return entry
    
    def stats(self) -> Dict:
        self.memory.reload()  # Sync with other processes
        return {
            "memory": self.memory.stats(),
            "graph": self.graph.stats(),
            "categories": list(self.context_vectors.vectors.keys()),
            "project_files": self.working_memory.get_file_count()
        }


import threading

# Global instance
_orchestrator: Optional[MemoryOrchestrator] = None
_orch_lock = threading.Lock()

def get_orchestrator() -> MemoryOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        with _orch_lock:
            if _orchestrator is None:
                _orchestrator = MemoryOrchestrator()
    return _orchestrator


def get_memory_context(query: str) -> str:
    """Convenience function: get context as string for prompts"""
    orch = get_orchestrator()
    ctx = orch.get_context(query)
    return ctx.to_prompt()
