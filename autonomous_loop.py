
import time
import sys
import random
import os
import json
import re
from datetime import datetime

# Force UTF-8 for Poetiq emojis
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

from core.poetiq import PoetiqRunner
from core.llm_client import LLMClient
from config.settings import (
    TEMPERATURE, 
    AUTO_SLEEP_INTERVAL, 
    AUTO_HEALTH_CHECK_EVERY, 
    AUTO_MAX_CONSECUTIVE_FAIL,
    AUTO_SUCCESS_SCORE,
    NUM_WORKERS
)
from utils.logger import get_logger
from utils.monitoring import get_monitoring_logger

# Configuration (from settings.py)
LOG_FILE = "autonomous.log"
CHECKPOINT_FILE = "autonomous_checkpoint.json"
SLEEP_INTERVAL = AUTO_SLEEP_INTERVAL
HEALTH_CHECK_INTERVAL = AUTO_HEALTH_CHECK_EVERY
MAX_CONSECUTIVE_FAILURES = AUTO_MAX_CONSECUTIVE_FAIL

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    
    # Safe print
    try:
        print(msg, flush=True)
    except:
        try:
            # Fallback to simple print if encoding/formatting fails
            print(message, flush=True)
        except:
            pass
            
    # File write removed to prevent lock contention with > redirection

def save_checkpoint(task_count: int, last_task: str = ""):
    """Save checkpoint to resume after restart"""
    checkpoint = {
        "task_count": task_count,
        "last_task": last_task,
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid()
    }
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(checkpoint, f)
    except:
        pass

def load_checkpoint() -> dict:
    """Load checkpoint from disk"""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"task_count": 0, "last_task": ""}

def parse_test_cases(task_text: str) -> list:
    """Extract test cases from task description.
    
    Supports multiple input formats:
    - solve('string') -> expected
    - solve("string") -> expected
    - solve(123) -> expected
    - solve(-5) -> expected (negative numbers)
    - solve(3.14) -> expected (floats)
    - solve([1, 2, 3]) -> expected
    - solve([[1,2],[3,4]]) -> expected (nested)
    - solve({'key': 'value'}) -> expected
    - solve(True) -> expected
    - solve((1, 2)) -> expected (tuples)
    """
    import ast
    
    test_cases = []
    
    # Common separator pattern: ->, ==, is, returns
    sep = r"\s*(?:->|==|is|returns)\s*"
    
    # Pattern 1: String inputs - func('...') or func("...")
    string_pattern = r"(?:solve|[\w_]+)\(['\"](.+?)['\"]\)" + sep + r"(.+)"
    for match in re.finditer(string_pattern, task_text, re.IGNORECASE):
        input_val = match.group(1)
        expected_raw = match.group(2).strip()
        expected = _safe_parse(expected_raw)
        test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 2: Numeric inputs - func(123), func(-5), func(3.14)
    numeric_pattern = r"(?:solve|[\w_]+)\((-?\d+\.?\d*)\)" + sep + r"(.+)"
    for match in re.finditer(numeric_pattern, task_text, re.IGNORECASE):
        input_raw = match.group(1)
        expected_raw = match.group(2).strip()
        
        input_val = _safe_parse(input_raw)
        expected = _safe_parse(expected_raw)
        
        if not any(tc["input"] == input_val for tc in test_cases):
            test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 3: Boolean inputs - func(True), func(False)
    bool_pattern = r"(?:solve|[\w_]+)\((True|False)\)" + sep + r"(.+)"
    for match in re.finditer(bool_pattern, task_text, re.IGNORECASE):
        input_raw = match.group(1)
        expected_raw = match.group(2).strip()
        
        input_val = _safe_parse(input_raw)
        expected = _safe_parse(expected_raw)
        
        if not any(tc["input"] == input_val for tc in test_cases):
            test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 4: List/dict/tuple inputs - func([...]), func({...}), func((...))
    # Uses balanced bracket matching (simple approximation)
    complex_pattern = r"(?:solve|[\w_]+)\((\[.*?\]|\{.*?\}|\(.*?\))\)" + sep + r"(.+)"
    for match in re.finditer(complex_pattern, task_text, re.IGNORECASE):
        input_raw = match.group(1)
        expected_raw = match.group(2).strip()
        
        input_val = _safe_parse(input_raw)
        expected = _safe_parse(expected_raw)
        
        if not any(tc["input"] == input_val for tc in test_cases):
            test_cases.append({"input": input_val, "expected": expected})
    
    return test_cases[:8]  # Increased max to 8 test cases


def _safe_parse(value_str: str):
    """Safely parse a string representation to Python value using ast.literal_eval."""
    import ast
    
    value_str = value_str.strip()
    
    # Clean up common markdown/formatting artifacts
    value_str = re.sub(r'^\*\*', '', value_str)  # Remove leading **
    value_str = re.sub(r'\*\*$', '', value_str)  # Remove trailing **
    value_str = re.sub(r'\s*\(.*$', '', value_str)  # Remove trailing explanations like "(Count of...)"
    value_str = value_str.strip()
    
    # Try ast.literal_eval first (safe for literals)
    try:
        return ast.literal_eval(value_str)
    except (ValueError, SyntaxError):
        pass
    
    # Handle common edge cases
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    if value_str.lower() == 'none':
        return None
    
    # Return as string if can't parse
    return value_str

def generate_task(runner):
    """
    Generate a task with INTELLIGENT CURRICULUM based on memory.
    
    Uses:
    - Error patterns from Curator (practice frequent errors)
    - Weak categories from AdaptiveDifficulty
    - Recent lessons from ReflectionBuffer
    - Dedicated slot for cache efficiency
    """
    from memory.adaptive_difficulty import get_difficulty_tracker
    from memory.test_patterns import get_test_patterns
    from memory.curator import get_curator
    from memory.reflection_buffer import get_reflection_buffer
    from config.settings import TASK_GENERATOR_SLOT
    
    tracker = get_difficulty_tracker()
    pattern_learner = get_test_patterns()
    curator = get_curator()
    
    # === MEMORY CONTEXT ===
    
    # 1. Get error patterns from Curator
    error_context = curator.get_error_summary_for_prompt()
    if error_context:
        log(f"🧠 Using error patterns for task targeting")
    
    # 2. Get weak categories from AdaptiveDifficulty
    should_target, weakness_category = tracker.should_target_weakness()
    
    # 3. Get recent lessons (avoid repeating mistakes)
    lesson_context = ""
    try:
        buffer = get_reflection_buffer()
        lessons = buffer.get_lessons()[-3:]  # Last 3 lessons
        if lessons:
            lesson_context = "\n## RECENT LESSONS (avoid these mistakes):\n"
            for lesson in lessons:
                lesson_context += f"- {lesson.get('lesson', '')[:80]}\n"
    except Exception:
        pass
    
    # === BUILD PROMPT ===
    
    # Get difficulty modifier
    difficulty_modifier = tracker.get_difficulty_prompt_modifier()
    
    # Build category selection
    target_category = None
    if should_target and weakness_category:
        category_instruction = f"FOCUS ON: {weakness_category.upper()} category"
        target_category = weakness_category
        log(f"🎯 Targeting weakness: {weakness_category}")
    else:
        category_instruction = (
            "PICK exactly ONE task from this list:\n"
            "- STRING: validate_email OR reverse_string OR count_vowels OR is_palindrome\n"
            "- MATH: fibonacci OR is_prime OR factorial OR sum_of_digits\n"
            "- LIST: find_duplicates OR remove_duplicates OR find_max\n"
            "- DICT: word_frequency OR invert_dict\n"
            "- VALIDATION: is_valid_url OR validate_phone"
        )
    
    # Get learned test pattern suggestions
    test_suggestions = ""
    if target_category:
        patterns = pattern_learner.get_patterns_for_category(target_category, n=2)
        if patterns:
            test_suggestions = "\n\nLEARNED TEST PATTERNS:\n"
            for p in patterns:
                test_suggestions += f"- Input: {p['input_type']}, Output: {p['output_type']}\n"
            log(f"📚 Using {len(patterns)} learned test patterns")
    
    # Combine memory context
    memory_context = ""
    if error_context:
        memory_context += f"\n{error_context}\n"
    if lesson_context:
        memory_context += f"\n{lesson_context}\n"
    
    prompt = (
        f"Generate ONE SPECIFIC coding task (NO CODE!).\n\n"
        f"{memory_context}"
        f"RULES:\n"
        f"1. Pick ONE operation from ONE category only!\n"
        f"2. DO NOT include any Python code or solution!\n"
        f"3. The function must be called `solve(input)` - nothing else!\n"
        f"4. Include exactly 3 test cases.\n\n"
        f"{difficulty_modifier}\n\n"
        f"{category_instruction}{test_suggestions}\n\n"
        f"EXAMPLE OF CORRECT FORMAT:\n"
        f"Category: STRING\n"
        f"Task: Implement `solve(input)` that returns True if input is a palindrome.\n"
        f"Test cases:\n"
        f"- solve('racecar') -> True\n"
        f"- solve('hello') -> False\n"
        f"- solve('level') -> True\n\n"
        f"NOW GENERATE A SIMILAR TASK (pick a DIFFERENT operation):"
    )
    
    try:
        client = LLMClient()
        # Use dedicated slot for cache efficiency
        task = client.generate(prompt, temp=TEMPERATURE, slot_id=TASK_GENERATOR_SLOT)
        return task.strip()
    except Exception as e:
        log(f"⚠️ Task Generation Failed: {e}. Fallback to random.")
        tasks = [
            "Category: STRING\nTask: Check if a string is a palindrome\nTest cases:\n- solve('racecar') -> True\n- solve('hello') -> False\n- solve('level') -> True",
            "Category: MATH\nTask: Check if a number is prime\nTest cases:\n- solve(7) -> True\n- solve(4) -> False\n- solve(11) -> True",
            "Category: LIST\nTask: Find duplicate elements in a list\nTest cases:\n- solve([1,2,2,3]) -> [2]\n- solve([1,1,1]) -> [1]\n- solve([1,2,3]) -> []",
        ]
        return random.choice(tasks)

def main():
    log("[START] Starting Autonomous Worker Loop...")
    
    # Load checkpoint to resume from previous run
    checkpoint = load_checkpoint()
    task_count = checkpoint.get("task_count", 0)
    if task_count > 0:
        log(f"📋 Resuming from checkpoint: {task_count} previous tasks")
    
    consecutive_failures = 0
    
    try:
        runner = PoetiqRunner(num_workers=NUM_WORKERS)
        llm_client = LLMClient()  # For health checks
        monitor = get_monitoring_logger()  # Night supervision
        log("✅ System Initialized. Entering loop.")
        
        while True:
            # Check stop signal
            try:
                with open("STOP_AUTONOMOUS", "r") as f:
                    log("🛑 STOP signal detected. Exiting.")
                    break
            except FileNotFoundError:
                pass

            # 0. BLOCKING CONNECTION CHECK (Wait for LLM)
            # Prevents learning from connection errors when server is down
            while True:
                health = llm_client.health_check()
                if health["healthy"]:
                    break
                else:
                    log(f"⚠️ LLM Server offline. Waiting for connection... (Error: {health.get('error', 'Unknown')})")
                    # Only log the hint once per downtime cycle to avoid spamming? 
                    # Actually, repeating it every 10s is fine for visibility in logs.
                    log("👉 Please start the server: scripts/start_llm.bat") 
                    time.sleep(10) # Wait 10s before retry
            
            # Health check every N tasks
            if task_count > 0 and task_count % HEALTH_CHECK_INTERVAL == 0:
                health = llm_client.health_check()
                if health["healthy"]:
                    log(f"💚 Health check passed ({health['latency_ms']:.0f}ms)")
                else:
                    log(f"💔 Health check failed: {health['error']}")
                    consecutive_failures += 1
            
            # Check if we need to trigger restart
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log("⚠️ Too many consecutive failures. Saving checkpoint...")
                save_checkpoint(task_count, "health_failure")
                
                # Check if running in Docker
                in_docker = os.environ.get("IN_DOCKER_CONTAINER", "") == "true"
                
                if in_docker:
                    # In Docker, just reset and continue - container can be restarted externally
                    log("🐳 Docker detected - resetting failure count and continuing...")
                    consecutive_failures = 0
                    runner = PoetiqRunner(num_workers=3)
                    llm_client = LLMClient()
                else:
                    # Local: try to restart server
                    log("🔄 Triggering self-restart via health_check.py...")
                    try:
                        from health_check import restart_server
                        success = restart_server()
                        if success:
                            consecutive_failures = 0
                            log("✅ Server restarted successfully!")
                            runner = PoetiqRunner(num_workers=NUM_WORKERS)
                            llm_client = LLMClient()
                        else:
                            log("❌ Restart failed. Waiting 60s before retry...")
                            time.sleep(60)
                    except Exception as e:
                        log(f"❌ Restart mechanism error: {e}. Resetting and continuing...")
                        consecutive_failures = 0  # Reset instead of blocking
                continue
            
            # 1. Generate Task
            task = generate_task(runner)
            log(f"📋 Generated Task: {task}")
            
            # 1.5 Extract test cases from task
            test_cases = parse_test_cases(task)
            if test_cases:
                log(f"🧪 Extracted {len(test_cases)} test cases for verification")
            
            # 2. Execute
            start_time = time.time()
            session_id = f"auto_{task_count}_{int(start_time)}"
            monitor.log_task_start(task, session_id)
            try:
                result = runner.run(task, test_cases=test_cases)
                duration = time.time() - start_time
                score = result.get('score', 0)
                log(f"✅ Task Completed ({duration:.1f}s). Score: {score}")
                
                # Reset failure counter on success
                if score >= AUTO_SUCCESS_SCORE:
                    consecutive_failures = 0
                
                # Log to monitor for night supervision
                monitor.log_task_complete(
                    session_id, score, duration,
                    verified=result.get('verification_passed', False),
                    skipped_refine=result.get('skipped_refine', False)
                )
                
                # Show global trend and metrics with ASCII visualization
                try:
                    stats = monitor.get_summary()
                    trend_data = monitor.get_trend_summary()
                    
                    # Build ASCII score boxes: |21.5|→|22.0|→|23.5|
                    sessions = trend_data.get('sessions', [])
                    if sessions:
                        scores = [s.get('avg_score', 0) for s in sessions[-5:]]
                        score_boxes = "→".join(f"|{s:.1f}|" for s in scores)
                    else:
                        score_boxes = "No history yet"
                    
                    log(f" ")
                    log(f"📊 GLOBAL ANALYTICS:")
                    log(f"   • Recent: {score_boxes}")
                    log(f"   • Trend:  {trend_data.get('sparkline', '─')} {trend_data.get('direction_icon', '→')} {trend_data.get('delta', 0):+.1f}")
                    log(f"   • Stats:  {stats['tasks_completed']} tasks | {trend_data.get('avg_all_time', 0):.1f} avg | Best: {trend_data.get('best_score', 0)}")
                    log(f"   • Health: {stats['health']}")
                    log(f" ")
                except Exception as e:
                    log(f"⚠️ Metrics Error: {e}")
                
                # Learn test patterns from successful verifications
                if result.get('verification_passed', False) and test_cases:
                    try:
                        from memory.test_patterns import get_test_patterns
                        pattern_learner = get_test_patterns()
                        learn_result = pattern_learner.learn_from_success(task, test_cases)
                        if learn_result.get('learned', 0) > 0:
                            log(f"📝 Learned {learn_result['learned']} test patterns")
                    except Exception as e:
                        log(f"⚠️ Pattern learning error: {e}")
                
                # Record result for adaptive difficulty
                try:
                    from memory.adaptive_difficulty import get_difficulty_tracker
                    tracker = get_difficulty_tracker()
                    
                    # Extract category from task (look for "Category:" line)
                    import re
                    category_match = re.search(r'Category:\s*(\w+)', task, re.IGNORECASE)
                    category = category_match.group(1).lower() if category_match else "general"
                    
                    # Determine success
                    is_success = score >= AUTO_SUCCESS_SCORE
                    
                    # Record to tracker
                    track_result = tracker.record_result(
                        category=category,
                        difficulty=tracker.get_current_difficulty(),
                        success=is_success,
                        score=score,
                        verified=result.get('verification_passed', False)
                    )
                    
                    if track_result.get('adjustment'):
                        log(f"📊 Difficulty adjustment: {track_result['adjustment']}")
                except Exception as e:
                    log(f"⚠️ Difficulty tracking error: {e}")
                
                # Tick Memory Curator (runs curation every 5 iterations in background)
                try:
                    from memory.curator import tick_curator
                    tick_curator()
                except Exception as e:
                    pass  # Non-critical, don't log
                
                task_count += 1
                
                # Checkpoint every 5 tasks
                if task_count % 5 == 0:
                    save_checkpoint(task_count, task)
                    log(f"💾 Checkpoint saved: {task_count} tasks completed")
                    
            except Exception as e:
                log(f"❌ Task Failed: {e}")
                monitor.log_error("task_execution", str(e), {"task": task[:50]})
                consecutive_failures += 1
            
            # 3. Sleep
            log(f"💤 Sleeping for {SLEEP_INTERVAL}s...")
            time.sleep(SLEEP_INTERVAL)
            
    except Exception as e:
        log(f"🔥 Critical Worker Failure: {e}")
        import traceback
        traceback.print_exc()
        save_checkpoint(task_count, f"critical_error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
