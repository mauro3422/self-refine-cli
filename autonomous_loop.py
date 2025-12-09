
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
    
    Looks for patterns like:
    - solve('input') -> expected
    - solve("input") -> expected
    """
    test_cases = []
    # Pattern: solve('...') -> ... or solve("...") -> ...
    pattern = r"solve\(['\"](.+?)['\"]\)\s*->\s*(.+)"
    for match in re.finditer(pattern, task_text):
        input_val = match.group(1)
        expected_raw = match.group(2).strip()
        
        # Try to parse expected value
        try:
            # Handle strings, ints, bools, etc.
            expected = eval(expected_raw)
        except:
            expected = expected_raw
        
        test_cases.append({
            "input": input_val,
            "expected": expected
        })
    
    return test_cases[:5]  # Max 5 test cases

def generate_task(runner):
    """Generate a meaningful task using the LLM itself."""
    prompt = (
        "Generate a CODING task that requires implementing a `solve(input)` function. "
        "PICK ONE category randomly from: "
        "1) STRING: validate email, reverse words, count vowels, check palindrome "
        "2) MATH: fibonacci nth, is_prime, factorial, sum of digits "
        "3) LIST: find duplicates, merge sorted lists, remove duplicates "
        "4) DICT: word frequency, group by key, invert dictionary "
        "5) VALIDATION: is_valid_url, parse_date, validate_phone "
        "\n\nFORMAT (REQUIRED):\n"
        "Task: [description]\n"
        "Test cases:\n"
        "- solve('input1') -> expected1\n"
        "- solve('input2') -> expected2\n"
        "- solve('input3') -> expected3\n"
        "\nReturn ONLY the formatted task with 3 test cases."
    )
    
    try:
        # We use a raw LLM call or a quick runner call to get the task
        # creating a light worker for this
        client = LLMClient()
        task = client.generate(prompt, temp=TEMPERATURE)  # Use settings
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
