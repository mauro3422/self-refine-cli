# Memory Learner v2 - Richer extraction from sessions
# Extracts: lessons, tools, errors, and creates weighted links
# Now integrates with MemoryEvolution for memory consolidation

from typing import Dict, List, Optional
from core.llm_client import LLMClient
from config.settings import (
    MEMORY_SLOT, 
    PATTERN_BATCH_SIZE, 
    HIGH_SCORE_SKIP_THRESHOLD,
    LOW_ITERATION_THRESHOLD,
    LIMIT_PATTERN_TASK,
    LIMIT_PATTERN_RESPONSE,
    LIMIT_ANALYSIS_TASK,
    LIMIT_ERROR_PREVIEW
)
from memory.base import get_memory
from memory.evolution import get_evolution
from memory.skill_harvester import get_harvester


# OPTIMIZATION 4: Batch pattern learning counter (global)
_successful_task_counter = 0

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
        NEW: Also learns success patterns from verified workers.
        """
        # Determine if session was successful
        success = final_score >= 18 and iterations <= 2
        improved = final_score > initial_score
        
        # OPTIMIZATION 4: Batch pattern learning - only every N successful tasks
        global _successful_task_counter
        success_patterns = []
        
        if success and workers_data:
            _successful_task_counter += 1
            
            # Only extract patterns every BATCH_SIZE successful tasks
            if _successful_task_counter >= PATTERN_BATCH_SIZE:
                success_patterns = self._learn_success_patterns(task, workers_data)
                _successful_task_counter = 0  # Reset counter
                print(f"  📚 Batch pattern learning triggered")
            
            # Always harvest skills (no LLM call, just code extraction)
            self._harvest_skills_from_workers(task, workers_data)
        
        # OPTIMIZATION 4b: Skip LLM lesson extraction for simple high-score tasks
        if final_score >= HIGH_SCORE_SKIP_THRESHOLD and iterations <= LOW_ITERATION_THRESHOLD:
            # High quality, simple task - use heuristic lesson instead of LLM
            lessons = [f"SUCCESS: {task[:LIMIT_ANALYSIS_TASK]}... completed with high score"]
            print(f"  ⚡ Skip lesson LLM (high score {final_score})")
        else:
            # Build analysis prompt with workers data
            prompt = self._build_analysis_prompt(
                task, initial_score, final_score, 
                iterations, tool_results, errors, workers_data
            )
            
            response = self.llm.generate(prompt, temp=0.3, slot_id=MEMORY_SLOT)
            
            # Extract structured lessons
            lessons = self._extract_lessons(response)
        
        # Add success patterns as lessons too
        lessons.extend(success_patterns)
        
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
            # Determine if this is a success pattern (higher importance for these!)
            is_success_pattern = lesson.startswith("PATTERN:")
            lesson_importance = 6 if is_success_pattern else base_importance
            
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
                # Better category for success patterns
                category = "code_pattern" if is_success_pattern else self._detect_category(lesson, tools_used)
                source = "verified_success" if is_success_pattern else ("refinement" if improved else "failure")
                
                entry = self.memory.add(
                    lesson=lesson,
                    category=category,
                    importance=lesson_importance,
                    source_type=source,
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
            "success_patterns": len(success_patterns),
            "success": success,
            "importance": base_importance
        }
    
    def _learn_success_patterns(self, task: str, workers_data: List[Dict]) -> List[str]:
        """
        NEW: Extract success patterns from verified workers.
        When a worker's code was verified (executed successfully), we learn what worked.
        """
        verified_workers = [w for w in workers_data if w.get('verified', False)]
        
        if not verified_workers:
            return []
        
        # Get the best verified worker (first attempt = cleanest solution)
        best = min(verified_workers, key=lambda w: w.get('attempts', 1))
        response_preview = best.get('response', '')[:LIMIT_PATTERN_RESPONSE]
        tool_used = best.get('tool', 'python_exec')
        
        # Extract pattern using LLM - IMPROVED PROMPT for abstraction
        prompt = f"""Extract an ABSTRACT success pattern from this verified code.

TASK TYPE: {task[:LIMIT_PATTERN_TASK]}
TOOL: {tool_used}
CODE PREVIEW: {response_preview}

INSTRUCTIONS:
1. Identify the HIGH-LEVEL APPROACH, not the specific code
2. Focus on the STRATEGY that made it work
3. NO code literals, NO regex, NO specific values

GOOD EXAMPLES:
- "For validation tasks, use regex with pattern matching and edge case testing"
- "For file operations, check existence first then read/write with error handling"
- "For parsing tasks, use try-except with fallback and input sanitization"

BAD EXAMPLES (DO NOT DO):
- "Use regex r'^[a-z]+$'" ← Too specific!
- "Import re module and use match()" ← Just code!
- "def validate(x): return bool(...)" ← This is code, not a pattern!

Output ONE line in this format:
PATTERN: For [task category], use [strategy] with [key technique]

PATTERN:"""
        
        try:
            pattern = self.llm.generate(prompt, temp=0.2, slot_id=MEMORY_SLOT)
            pattern = pattern.strip()
            
            # DEBUG: Log what LLM returned
            print(f"  [DEBUG] Pattern LLM raw ({len(pattern)} chars): {pattern[:60]}...")
            
            # Clean up the pattern - extract first line/sentence only
            if '\n' in pattern:
                pattern = pattern.split('\n')[0].strip()
            if '. ' in pattern and len(pattern) > 150:
                pattern = pattern.split('. ')[0] + '.'
            
            # Clean up the pattern
            if not pattern.startswith("PATTERN:"):
                pattern = f"PATTERN: {pattern}"
            
            # Truncate if too long
            if len(pattern) > 150:
                pattern = pattern[:147] + "..."
            
            # Validate length (now more lenient)
            if len(pattern) > 20:
                print(f"  ✨ Success pattern: {pattern[:60]}...")
                return [pattern]
            else:
                print(f"  [DEBUG] Pattern rejected: too short ({len(pattern)} chars)")
        except Exception as e:
            print(f"  [DEBUG] Pattern extraction error: {e}")
        
        return []
    
    def _harvest_skills_from_workers(self, task: str, workers_data: List[Dict]):
        """
        NEW: Harvest executable functions from verified workers as reusable skills.
        Uses DreamCoder-inspired skill extraction.
        """
        verified = [w for w in workers_data if w.get('verified', False)]
        if not verified:
            return
        
        harvester = get_harvester()
        total_skills = 0
        
        for worker in verified:
            # Get the actual code from the worker
            code = self._extract_code_from_worker(worker)
            if code and len(code) > 50:  # Skip trivial code
                skills = harvester.harvest_from_code(code, task)
                total_skills += len(skills)
        
        if total_skills > 0:
            print(f"  🔧 Harvested {total_skills} skills from {len(verified)} verified workers")
    
    def _extract_code_from_worker(self, worker: Dict) -> Optional[str]:
        """Extract Python code from worker response"""
        import re
        response = worker.get('response', '')
        
        # Try to find code block
        match = re.search(r'```python\s*\n(.+?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try JSON format
        match = re.search(r'"code"\s*:\s*"([^"]+)"', response)
        if match:
            return match.group(1).replace('\\n', '\n')
        
        return None
    
    def _build_analysis_prompt(self, task, initial, final, iterations, tools, errors, workers_data=None):
        """Build a strict, concise prompt that generates actionable rules"""
        tools_str = ", ".join(tools.keys()) if isinstance(tools, dict) else str(tools) if tools else "None"
        errors_str = errors[0][:LIMIT_ERROR_PREVIEW] if errors else "None"
        
        # Simplified workers summary
        workers_summary = ""
        if workers_data:
            tools_used = [w.get('tool', 'none') for w in workers_data if w.get('tool')]
            workers_summary = f"Workers used: {', '.join(set(tools_used))}" if tools_used else ""
        
        success = "SUCCESS" if final >= 18 else "PARTIAL" if final >= 12 else "FAIL"
        
        return f"""Extract ONE actionable, GENERALIZED rule from this session.

TASK: {task[:LIMIT_ANALYSIS_TASK]}
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
