import json

with open('data/agent_memory.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

memories = data.get('memories', [])
print(f"Total memories: {len(memories)}\n")

# Find PATTERN lessons
patterns = [m for m in memories if m.get('lesson', '').startswith('PATTERN:')]
print(f"=== PATTERN LESSONS ({len(patterns)}) ===")
for m in patterns:
    print(f"  - {m.get('lesson', '')[:80]}")
    print(f"    Source: {m.get('source_type')}, Category: {m.get('category')}")
    print()

# Find verified_success sources
verified = [m for m in memories if m.get('source_type') == 'verified_success']
print(f"\n=== VERIFIED_SUCCESS LESSONS ({len(verified)}) ===")
for m in verified[:5]:
    print(f"  - {m.get('lesson', '')[:80]}")

# Show 5 most recent
print("\n=== 5 MOST RECENT ===")
recent = sorted(memories, key=lambda x: x.get('created', ''), reverse=True)[:5]
for m in recent:
    print(f"  - [{m.get('category')}] {m.get('source_type')}")
    print(f"    {m.get('lesson', '')[:60]}...")
    print()
