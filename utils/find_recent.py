
import os
import time

def find_recent():
    now = time.time()
    limit = 600 # 10 minutes
    print("Searching for recently modified files...")
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            full_path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(full_path)
                if now - mtime < limit:
                    # Ignore our own monitoring scripts
                    if f in ["autonomous.log", "find_recent.py", "tail_log.py", "read_autonomous_log.py", "robust_tail.py", "get_last_task.py", "check_autonomous.py", "kill_autonomous.py"]:
                         continue
                    print(f"FOUND: {full_path}")
            except:
                pass

if __name__ == "__main__":
    find_recent()
