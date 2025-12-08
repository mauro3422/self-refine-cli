
import re

LOG_FILE = "autonomous.log"

def get_last_task():
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            matches = re.findall(r"Generated Task: (.*)", content)
            if matches:
                print(f"Found {len(matches)} tasks.")
                print("Last 5 Tasks:")
                for task in matches[-5:]:
                    print(f"- {task.strip()}")
            else:
                print("No tasks found in log.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_last_task()
