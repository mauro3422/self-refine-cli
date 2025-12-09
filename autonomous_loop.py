
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
    AUTO_SUCCESS_SCORE
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
            print(msg.encode('ascii', 'ignore').decode('ascii'), flush=True)
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
    
    # Pattern 1: String inputs - solve('...') or solve("...")
    string_pattern = r"solve\(['\"](.+?)['\"]\)\s*->\s*(.+)"
    for match in re.finditer(string_pattern, task_text):
        input_val = match.group(1)
        expected_raw = match.group(2).strip()
        expected = _safe_parse(expected_raw)
        test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 2: Numeric inputs - solve(123), solve(-5), solve(3.14)
    numeric_pattern = r"solve\((-?\d+\.?\d*)\)\s*->\s*(.+)"
    for match in re.finditer(numeric_pattern, task_text):
        input_raw = match.group(1)
        expected_raw = match.group(2).strip()
        
        input_val = _safe_parse(input_raw)
        expected = _safe_parse(expected_raw)
        
        if not any(tc["input"] == input_val for tc in test_cases):
            test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 3: Boolean inputs - solve(True), solve(False)
    bool_pattern = r"solve\((True|False)\)\s*->\s*(.+)"
    for match in re.finditer(bool_pattern, task_text):
        input_raw = match.group(1)
        expected_raw = match.group(2).strip()
        
        input_val = _safe_parse(input_raw)
        expected = _safe_parse(expected_raw)
        
        if not any(tc["input"] == input_val for tc in test_cases):
            test_cases.append({"input": input_val, "expected": expected})
    
    # Pattern 4: List/dict/tuple inputs - solve([...]), solve({...}), solve((...))
    # Uses balanced bracket matching
    complex_pattern = r"solve\((\[.*?\]|\{.*?\}|\(.*?\))\)\s*->\s*(.+)"
    for match in re.finditer(complex_pattern, task_text):
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
    """Generate a task with ADAPTIVE DIFFICULTY based on performance history."""
    from memory.adaptive_difficulty import get_difficulty_tracker
    from memory.test_patterns import get_test_patterns
    
    tracker = get_difficulty_tracker()
    pattern_learner = get_test_patterns()
    
    # Check if we should target a weakness category
    should_target, weakness_category = tracker.should_target_weakness()
    
    # Get difficulty modifier
    difficulty_modifier = tracker.get_difficulty_prompt_modifier()
    
    # Build category selection
    target_category = None
    if should_target and weakness_category:
        # Target the weak category
        category_instruction = f"FOCUS ON: {weakness_category.upper()} category (this is a weakness area that needs practice)"
        target_category = weakness_category
        log(f"🎯 Targeting weakness: {weakness_category}")
    else:
        # Normal random selection
        category_instruction = (
            "PICK ONE category randomly from: "
            "1) STRING: validate email, reverse words, count vowels, check palindrome "
            "2) MATH: fibonacci nth, is_prime, factorial, sum of digits "
            "3) LIST: find duplicates, merge sorted lists, remove duplicates "
            "4) DICT: word frequency, group by key, invert dictionary "
            "5) VALIDATION: is_valid_url, parse_date, validate_phone "
        )
    
    # Get learned test pattern suggestions
    test_suggestions = ""
    if target_category:
        patterns = pattern_learner.get_patterns_for_category(target_category, n=2)
        if patterns:
            test_suggestions = "\n\nLEARNED TEST PATTERNS (use similar patterns):\n"
            for p in patterns:
                test_suggestions += f"- Input type: {p['input_type']}, Output type: {p['output_type']}\n"
            log(f"📚 Using {len(patterns)} learned test patterns")
    
    prompt = (
        f"Generate a CODING task that requires implementing a `solve(input)` function.\n\n"
        f"{difficulty_modifier}\n\n"
        f"{category_instruction}{test_suggestions}\n\n"
        f"FORMAT (REQUIRED):\n"
        f"Category: [category_name]\n"
        f"Task: [description]\n"
        f"Test cases:\n"
        f"- solve('input1') -> expected1\n"
        f"- solve('input2') -> expected2\n"
        f"- solve('input3') -> expected3\n"
        f"\nReturn ONLY the formatted task with 3 test cases."
    )
    
    try:
        client = LLMClient()
        task = client.generate(prompt, temp=TEMPERATURE)
        return task.strip()
    except Exception as e:
        log(f"⚠️ Task Generation Failed: {e}. Fallback to random.")
        tasks = [
            "Analiza memory/orchestrator.py y mejora la documentacion",
            "Escribe un test simple para tools/file_tools.py",
            "Busca y reporta TODOs en el proyecto",
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
        runner = PoetiqRunner(num_workers=3)
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
                log("🔄 Triggering self-restart via health_check.py...")
                
                # Try to recover by importing and calling restart
                try:
                    from health_check import restart_server
                    success = restart_server()
                    if success:
                        consecutive_failures = 0
                        log("✅ Server restarted successfully!")
                        # Recreate the runner with fresh connection
                        runner = PoetiqRunner(num_workers=3)
                        llm_client = LLMClient()
                    else:
                        log("❌ Restart failed. Waiting 60s before retry...")
                        time.sleep(60)
                except Exception as e:
                    log(f"❌ Restart mechanism error: {e}. Waiting 60s...")
                    time.sleep(60)
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
        save_checkpoint(task_count, f"critical_error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
