# Agent Memory - IMPROVED: Learns from errors automatically

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import OUTPUT_DIR


class AgentMemory:
    """Persistent memory that learns from Self-Refine corrections"""
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(OUTPUT_DIR, "agent_memory.json")
        self.memories: List[Dict[str, Any]] = []
        self.session_learnings: List[str] = []  # Learnings from current session
        self._load()
    
    def _load(self):
        """Load memories from disk"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get("memories", [])
            except:
                self.memories = []
    
    def _save(self):
        """Save memories to disk"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({
                "memories": self.memories,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
    
    def learn_from_refinement(self, 
                               original_response: str,
                               refined_response: str, 
                               feedback: str,
                               score_before: int,
                               score_after: int):
        """
        Learn from a Self-Refine iteration.
        Called when score improves significantly.
        """
        if score_after <= score_before:
            return  # No improvement, nothing to learn
        
        improvement = score_after - score_before
        
        # Extract what was wrong and how it was fixed
        lesson = {
            "type": "refinement",
            "what_was_wrong": self._extract_problem(feedback),
            "improvement": improvement,
            "timestamp": datetime.now().isoformat()
        }
        
        self.memories.append(lesson)
        self.session_learnings.append(lesson["what_was_wrong"])
        self._save()
        
        if improvement >= 5:
            print(f"  💡 Aprendí: {lesson['what_was_wrong'][:60]}...")
    
    def learn_from_tool_mistake(self, required_tools: List[str], used_tools: List[str]):
        """Learn when tools weren't used correctly"""
        missing = set(required_tools) - set(used_tools)
        if not missing:
            return
        
        lesson = {
            "type": "tool_usage",
            "what_was_wrong": f"Debí usar {list(missing)} pero no lo hice",
            "required": required_tools,
            "used": used_tools,
            "timestamp": datetime.now().isoformat()
        }
        
        self.memories.append(lesson)
        self.session_learnings.append(lesson["what_was_wrong"])
        self._save()
        print(f"  💡 Aprendí: Debo usar {list(missing)} cuando me piden leer/ejecutar")
    
    def _extract_problem(self, feedback: str) -> str:
        """Extract the main problem from feedback"""
        # Look for common patterns
        lines = feedback.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in ['error', 'wrong', 'incorrecto', 'falta', 'missing', 'no usó']):
                return line.strip()[:100]
        
        # Return first substantive line
        for line in lines:
            if len(line.strip()) > 20:
                return line.strip()[:100]
        
        return "Respuesta necesitaba mejoras"
    
    def get_relevant_context(self, query: str) -> str:
        """Get relevant memories for a query"""
        if not self.memories:
            return ""
        
        # Get recent learnings
        recent = self.memories[-10:]
        
        context_lines = ["LECCIONES ANTERIORES (evita estos errores):"]
        for m in recent:
            if m.get("what_was_wrong"):
                context_lines.append(f"- {m['what_was_wrong']}")
        
        if len(context_lines) == 1:
            return ""
        
        return "\n".join(context_lines)
    
    def get_session_summary(self) -> str:
        """Get summary of what was learned this session"""
        if not self.session_learnings:
            return "No se aprendió nada nuevo esta sesión."
        
        return f"Aprendizajes de esta sesión:\n" + "\n".join(f"- {l}" for l in self.session_learnings)
    
    def stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        types = {}
        for m in self.memories:
            t = m.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        
        return {
            "total": len(self.memories),
            "by_type": types,
            "session_learnings": len(self.session_learnings)
        }
    
    def clear(self):
        """Clear all memories"""
        self.memories = []
        self.session_learnings = []
        self._save()
        print("🧹 Memoria completamente limpiada")


# Global instance
_memory: Optional[AgentMemory] = None

def get_memory() -> AgentMemory:
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
