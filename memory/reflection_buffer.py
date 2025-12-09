# Reflexion Buffer - Intra-session Learning
# Persists lessons learned during refinement to avoid repeating errors

from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class Reflection:
    """A single reflection/lesson learned during refinement"""
    iteration: int
    error_type: str
    error_summary: str
    lesson: str
    

class ReflectionBuffer:
    """
    Persists lessons learned WITHIN a session.
    
    Problem solved:
    - Without this, iteration 4 might repeat the same error from iteration 1
    - The SelfRefiner "forgets" what it tried before
    
    Usage:
    1. After each failed iteration, add a reflection
    2. Before each new iteration, inject get_context() into the prompt
    """
    
    MAX_REFLECTIONS = 5  # Keep last N reflections to avoid context bloat
    
    def __init__(self):
        self.reflections: List[Reflection] = []
        self.session_id: str = ""
    
    def start_session(self, session_id: str):
        """Reset buffer for new session"""
        self.reflections = []
        self.session_id = session_id
    
    def add(self, iteration: int, error: str, lesson: str):
        """
        Add a reflection after a failed iteration.
        
        Args:
            iteration: Which iteration this was (1, 2, 3...)
            error: What went wrong (error message or type)
            lesson: What to do differently next time
        """
        # Extract error type from error message
        error_type = "Error"
        if "Error:" in error:
            error_type = error.split(":")[0].split()[-1]
        
        reflection = Reflection(
            iteration=iteration,
            error_type=error_type,
            error_summary=error[:100],
            lesson=lesson
        )
        
        self.reflections.append(reflection)
        
        # Keep only last N reflections
        if len(self.reflections) > self.MAX_REFLECTIONS:
            self.reflections = self.reflections[-self.MAX_REFLECTIONS:]
        
        print(f"    📝 Reflection added: {lesson[:50]}...")
    
    def add_from_error(self, iteration: int, error: str):
        """
        Automatically generate a lesson from an error.
        Uses simple heuristics - for complex cases, use add() with explicit lesson.
        """
        lessons = {
            "IndexError": "Check list/array bounds before accessing",
            "KeyError": "Verify key exists in dict before accessing",
            "TypeError": "Ensure types are compatible before operations", 
            "ImportError": "Use only standard library imports, define functions inline",
            "ModuleNotFoundError": "Don't import from project files, implement inline",
            "NameError": "Define all variables before using them",
            "SyntaxError": "Check parentheses, quotes, colons, and indentation",
            "AttributeError": "Verify object has the attribute/method before calling",
            "ValueError": "Validate input data format and range",
            "ZeroDivisionError": "Check divisor is not zero before dividing",
        }
        
        # Find matching lesson
        lesson = "Review and fix the error"
        for error_type, error_lesson in lessons.items():
            if error_type in error:
                lesson = error_lesson
                break
        
        self.add(iteration, error, lesson)
    
    def get_context(self) -> str:
        """
        Get reflections formatted for injection into LLM prompt.
        Returns empty string if no reflections yet.
        """
        if not self.reflections:
            return ""
        
        lines = ["## LECCIONES DE ESTA SESIÓN (NO repetir estos errores):"]
        
        for r in self.reflections:
            lines.append(f"- Iter {r.iteration}: {r.error_type} → {r.lesson}")
        
        return "\n".join(lines)
    
    def has_reflections(self) -> bool:
        """Check if there are any reflections to inject"""
        return len(self.reflections) > 0
    
    def get_stats(self) -> Dict:
        """Get statistics about reflections"""
        if not self.reflections:
            return {"count": 0, "error_types": []}
        
        error_types = list(set(r.error_type for r in self.reflections))
        return {
            "count": len(self.reflections),
            "error_types": error_types,
            "iterations_with_errors": [r.iteration for r in self.reflections]
        }


# Global instance for the session
_buffer = ReflectionBuffer()


def get_buffer() -> ReflectionBuffer:
    """Get the global reflection buffer instance"""
    return _buffer


# Quick test
if __name__ == "__main__":
    buffer = ReflectionBuffer()
    buffer.start_session("test_session")
    
    buffer.add_from_error(1, "IndexError: list index out of range")
    buffer.add_from_error(2, "ModuleNotFoundError: No module named 'utils.validators'")
    buffer.add(3, "Logic error", "Use try-except for edge cases")
    
    print("\n=== Reflection Buffer Test ===\n")
    print(buffer.get_context())
    print("\nStats:", buffer.get_stats())
