# Memory Learner v2 - Richer extraction from sessions
# Extracts: lessons, tools, errors, and creates weighted links
# Now integrates with MemoryEvolution for memory consolidation

from typing import Dict, List, Optional
from core.llm_client import LLMClient
from memory.base import get_memory
from memory.evolution import get_evolution


class MemoryLearner:
    """
    Agent that learns from completed sessions.
    Extracts rich information for memory graph.
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.memory = get_memory()
    
    def learn_from_session(self, 
                           task: str, 
                           initial_score: int,
                           final_score: int,
                           iterations: int,
                           tool_results: Dict = None,
                           errors: List[str] = None,
                           workers_data: List[Dict] = None) -> Dict:
        """
        Analyze a session and extract lessons with rich metadata.
        Now accepts workers_data for richer learning context.
        """
        # Determine if session was successful
        success = final_score >= 18 and iterations <= 2
        improved = final_score > initial_score
        
        # Build analysis prompt with workers data
        prompt = self._build_analysis_prompt(
            task, initial_score, final_score, 
            iterations, tool_results, errors, workers_data
        )
        
        response = self.llm.generate(prompt, temp=0.3)
        
        # Extract structured lessons
        lessons = self._extract_lessons(response)
        
        # Determine metadata for each lesson
        tools_used = list(tool_results.keys()) if tool_results else []
        error_types = self._categorize_errors(errors) if errors else []
        
        # Calculate importance based on session
        base_importance = 5
        if not success:
            base_importance = 7  # Failures are more important to remember
        if errors:
            base_importance = 8  # Errors are very important
        
        # Add each lesson with rich metadata
        added = []
        evolved = []
        evolution = get_evolution()
        
        for lesson in lessons:
            # NEW: Check for memories that should evolve
            candidates = evolution.get_evolution_candidates(lesson, self.memory.memories)
            for old_mem in candidates:
                evolved_data = evolution.evolve_memory(old_mem, lesson)
                # Update the old memory in-place
                old_mem.update(evolved_data)
                evolved.append(old_mem.get("id"))
                print(f"  🔄 Evolved memory #{old_mem.get('id')}: {evolved_data['lesson'][:50]}...")
            
            # Add new memory if no evolution happened
            if not candidates:
                entry = self.memory.add(
                    lesson=lesson,
                    category=self._detect_category(lesson, tools_used),
                    importance=base_importance,
                    source_type="refinement" if improved else "failure",
                    tools_involved=tools_used,
                    error_type=error_types[0] if error_types else None
                )
                added.append(entry)
        
        # Save if we evolved any memories
        if evolved:
            self.memory._save()
        
        return {
            "lessons_added": len(added),
            "lessons_evolved": len(evolved),
            "success": success,
            "importance": base_importance
        }
    
    def _build_analysis_prompt(self, task, initial, final, iterations, tools, errors, workers_data=None):
        """Build a strict, concise prompt that generates actionable rules"""
        tools_str = ", ".join(tools.keys()) if isinstance(tools, dict) else str(tools) if tools else "None"
        errors_str = errors[0][:100] if errors else "None"
        
        # Simplified workers summary
        workers_summary = ""
        if workers_data:
            tools_used = [w.get('tool', 'none') for w in workers_data if w.get('tool')]
            workers_summary = f"Workers used: {', '.join(set(tools_used))}" if tools_used else ""
        
        success = "SUCCESS" if final >= 18 else "PARTIAL" if final >= 12 else "FAIL"
        
        return f"""Extract ONE actionable, GENERALIZED rule from this session.

TASK: {task[:150]}
RESULT: {success} (score {initial}→{final}/25, {iterations} iterations)
TOOLS: {tools_str}
ERROR: {errors_str}
{workers_summary}

OUTPUT FORMAT (pick ONE):
RULE: When [general situation], use [tool_name](param=[placeholder])
AVOID: Don't [general mistake] because [reason]

CRITICAL - GENERALIZATION RULES:
- Do NOT use specific file names like 'sandbox/foo.py' → use [file] or [target_file]
- Do NOT use specific variable names → use [variable], [function], [class]
- Do NOT use specific paths → use [directory], [path], [workspace]
- The rule should apply to ANY similar situation, not just this specific task

REQUIREMENTS:
- Use EXACT tool names: read_file, write_file, python_exec, list_dir, search_files, replace_in_file
- Use placeholders: [file], [content], [code], [target], [replacement], [pattern]
- ONE sentence max, no fluff
- If session was trivial, output: SKIP

YOUR GENERALIZED RULE:"""
    
    def _extract_lessons(self, text: str) -> List[str]:
        """Extract lessons from LLM response - handles multiple formats"""
        lessons = []
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip empty or too short lines
            if len(line) < 10:
                continue
            
            # Pattern 1: Bullet points (-, •, *)
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                lesson = line.lstrip('-•*').strip()
            # Pattern 2: Numbered lists (1., 2., 1), 2))
            elif len(line) > 2 and line[0].isdigit() and line[1] in '.):':
                lesson = line[2:].strip()
            elif len(line) > 3 and line[:2].isdigit() and line[2] in '.):':
                lesson = line[3:].strip()
            else:
                continue
            
            # Validate lesson length
            if len(lesson) > 15 and len(lesson) < 300:
                lessons.append(lesson)
        
        # Fallback: if no lessons found, use first substantive sentence
        if not lessons and len(text) > 30:
            # Take first sentence-like chunk
            sentences = text.split('.')
            for s in sentences[:2]:
                s = s.strip()
                if len(s) > 20 and len(s) < 200:
                    lessons.append(s)
                    break
        
        return lessons[:2]
    
    def _detect_category(self, lesson: str, tools: List[str]) -> str:
        """Use unified ContextVectors for category detection"""
        from memory.context_vectors import get_context_vectors
        cv = get_context_vectors()
        category, confidence = cv.detect_category(lesson)
        
        # Fallback: if low confidence, use tools to infer
        if confidence < 0.1 and tools:
            if "write_file" in tools:
                return "file_create"
            elif "read_file" in tools:
                return "file_read"
            elif "python_exec" in tools:
                return "code_exec"
        
        return category if confidence >= 0.1 else "general"
    
    def _categorize_errors(self, errors: List[str]) -> List[str]:
        categories = []
        for e in errors:
            e_lower = e.lower()
            if "parse" in e_lower or "json" in e_lower:
                categories.append("parsing")
            elif "timeout" in e_lower:
                categories.append("timeout")
            elif "not found" in e_lower or "missing" in e_lower:
                categories.append("not_found")
            else:
                categories.append("unknown")
        return categories
    
    def mark_lesson_helpful(self, lesson_text: str) -> None:
        """Mark a lesson as helpful (strengthen it)"""
        for mem in self.memory.memories:
            if lesson_text[:50] in mem.get("lesson", ""):
                self.memory.mark_success(mem["id"])
                break
    
    def mark_lesson_unhelpful(self, lesson_text: str) -> None:
        """Mark a lesson as unhelpful (weaken it)"""
        for mem in self.memory.memories:
            if lesson_text[:50] in mem.get("lesson", ""):
                self.memory.mark_failure(mem["id"])
                break


def learn_from_session(**kwargs) -> Dict:
    learner = MemoryLearner()
    return learner.learn_from_session(**kwargs)
