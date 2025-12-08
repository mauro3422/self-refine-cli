
import json
import os
from datetime import datetime

MEMORY_FILE = "data/agent_memory.json"

def dump_memory():
    if not os.path.exists(MEMORY_FILE):
        print("Memory file not found.")
        return

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            memories = data.get("memories", [])
            print(f"Total Memories: {len(memories)}")
            
            # Filter for today's memories (Dec 7 2025)
            today_str = "2025-12-07"
            todays_memories = [m for m in memories if m.get("created_at", "").startswith(today_str)]
            
            print(f"Memories created Today ({today_str}): {len(todays_memories)}")
            
            print("\n--- Last 5 Memories ---")
            for m in memories[-5:]:
                print(f"[{m.get('created_at')}] Score:{m.get('importance')} - {m.get('lesson')[:100]}...")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_memory()
