# Simple test to debug scoring
import sys
sys.path.insert(0, '.')

from core.llm_client import LLMClient
from core.agent import extract_score, SELF_EVAL_PROMPT

# Test the score extraction
test_feedbacks = [
    "TOTAL_SCORE: 23/25",
    "TOTAL: 20/25",
    "Score: 18/25",
    "Tool usage: 4/5\nAccuracy: 5/5\nCompleteness: 4/5\nClarity: 5/5\nUsefulness: 5/5",
    "1. Tool usage: 5/5\n2. Accuracy: 4/5\n3. Completeness: 5/5\n4. Clarity: 4/5\n5. Usefulness: 5/5",
]

print("="*50)
print("Testing score extraction:")
print("="*50)

for fb in test_feedbacks:
    score = extract_score(fb)
    print(f"\nInput: {fb[:60]}...")
    print(f"Extracted score: {score}/25")

print("\n" + "="*50)
print("Testing actual LLM evaluation:")
print("="*50)

llm = LLMClient()

# Simple evaluation
eval_prompt = SELF_EVAL_PROMPT.format(
    user_input="list files in tools/ and explain each",
    tools_used="list_dir",
    response="The tools folder contains: base.py (tool base class), file_tools.py (read/write files), command_tools.py (run commands), registry.py (tool registry)"
)

print("\nSending evaluation prompt to LLM...")
print("-"*50)

feedback = llm.generate(eval_prompt, temp=0.3)
print(f"\nLLM Feedback:\n{feedback}")
print("-"*50)

score = extract_score(feedback)
print(f"\n✅ Extracted score: {score}/25")

if score >= 22:
    print("🎉 OPTIMAL!")
elif score > 0:
    print("⚠️ Needs refinement")
else:
    print("❌ Score extraction failed!")
