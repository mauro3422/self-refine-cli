# Fix slot_id=10 bug - Server only has 3 slots (0,1,2)
# Change slot_id=10 to slot_id=-1 (use any available slot)

def fix_slot_ids():
    files = ['memory/evolution.py', 'memory/llm_linker.py']
    fixed = 0
    
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'slot_id=10' in content:
                content = content.replace('slot_id=10', 'slot_id=-1')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"FIXED: {path} (slot_id=10 -> slot_id=-1)")
                fixed += 1
            else:
                print(f"OK: {path} (no slot_id=10 found)")
        except Exception as e:
            print(f"ERROR: {path} - {e}")
    
    return fixed

if __name__ == "__main__":
    print("=== Fixing slot_id=10 bug ===")
    fixed = fix_slot_ids()
    print(f"\n=== Fixed {fixed} file(s) ===")
