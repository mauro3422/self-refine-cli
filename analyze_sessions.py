import os
import json
from datetime import datetime

sessions_dir = 'outputs/sessions'
sessions = sorted(os.listdir(sessions_dir))

print("=== ALL SESSIONS ANALYSIS ===\n")

total_verified = 0
total_workers = 0
sessions_with_verified = 0

for filename in sessions:
    filepath = os.path.join(sessions_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find parallel phase
        parallel = None
        refine = None
        for event in data.get('events', []):
            if event.get('phase') == 'parallel':
                parallel = event
            if event.get('phase') == 'refine':
                refine = event
        
        if parallel:
            workers = parallel.get('workers', [])
            verified = sum(1 for w in workers if w.get('verified', False))
            total = len(workers)
            
            total_verified += verified
            total_workers += total
            
            if verified > 0:
                sessions_with_verified += 1
            
            # Show details
            status = "✅" if verified > 0 else "❌"
            iter_count = refine.get('iteration', 'N/A') if refine else 'N/A'
            skip = "SKIP" if refine and refine.get('iteration') == 0 else ""
            
            print(f"{status} {filename}: {verified}/{total} verified | iter={iter_count} {skip}")
            
            # Show error details for failed workers
            if verified == 0:
                for w in workers[:1]:  # Just first worker
                    err = w.get('execution_result', '')[:60]
                    print(f"   └─ Error preview: {err}")
    except Exception as e:
        print(f"⚠️ {filename}: Error reading - {e}")

print(f"\n=== SUMMARY ===")
print(f"Total sessions: {len(sessions)}")
print(f"Sessions with verified: {sessions_with_verified}")
print(f"Total workers verified: {total_verified}/{total_workers}")
print(f"Verification rate: {total_verified/total_workers*100:.1f}%" if total_workers > 0 else "N/A")
