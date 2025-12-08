
import re

LOG_FILE = "autonomous.log"

def extract_learnings():
    count = 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "Learned:" in line:
                    # Clean up timestamp if present
                    clean_line = line.strip()
                    # Try to extract just the message
                    match = re.search(r"Learned: (.*)", clean_line)
                    if match:
                        print(f"- {match.group(1)}")
                    else:
                        print(f"- {clean_line}")
                    count += 1
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\nTotal Learnings found: {count}")

if __name__ == "__main__":
    extract_learnings()
