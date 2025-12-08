
import os
import sys

# Force utf-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

LOG_FILE = "autonomous.log"

if os.path.exists(LOG_FILE):
    print(f"--- Reading {LOG_FILE} (Last 2000 chars) ---")
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            # Get last 2000 chars
            last_chunk = content[-2000:]
            
            # Force ASCII only for console compatibility
            clean_content = last_chunk.encode('ascii', 'ignore').decode('ascii')
            print(clean_content)
    except Exception as e:
        print(f"Error reading file: {e}")
    print("\n--- End of Log ---")
else:
    print(f"File {LOG_FILE} not found.")
