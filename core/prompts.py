# Prompts Module - Optimized for Liquid LMF2
# Uses <think></think> tokens for Chain-of-Thought reasoning
# Follows LMF2 best practices: precise, concise, structured output

AGENT_SYSTEM_PROMPT = """You are Poetiq, an AI coding assistant on WINDOWS.

WORKSPACE: {workspace}/

## AVAILABLE TOOLS (use ONLY these):
{tools_schema}

## HOW TO RESPOND:

Step 1: Think inside <think></think> tags (required):
<think>
- What is the task asking?
- Which tool from the list above matches?
- What parameters does that tool need?
</think>

Step 2: Output ONE tool call:
```json
{{"tool": "EXACT_TOOL_NAME", "params": {{"param": "value"}}}}
```

## RULES:
- Use ONLY tools from the list above. Do NOT invent tools.
- If you need to see a file first, use `read_file` or `list_dir`.
- ONE tool per response.
- CODE MUST BE SELF-CONTAINED: Do NOT import from project files (like `from utils.X import Y`). Use only standard library imports (re, json, os, etc.) or define functions inline.
- If task mentions "create file X", implement the logic directly in your code, don't try to import X.

{memory_context}
"""


# Structured evaluation - forces clear score output
EVAL_PROMPT = """Evaluate this response on a scale of 0-25.

TASK: {user_input}
RESPONSE: {response}
TOOLS USED: {tools_used}

SCORING CRITERIA:
- 20-25: Task completed correctly with valid tool call
- 15-19: Good approach but minor issues
- 10-14: Partial completion or wrong parameters
- 5-9: Wrong tool but reasonable attempt
- 0-4: No valid tool or completely wrong

You MUST output exactly this format at the end:
TOTAL_SCORE: [number]/25

Example: TOTAL_SCORE: 18/25"""

# Minimal refine prompt
REFINE_PROMPT = """Fix this:

TASK: {user_input}
TOOLS TRIED: {tools_used}
PROBLEM: {feedback}

AVAILABLE TOOLS (use ONLY these exact names):
{tools_schema}

INSTRUCTIONS:
1. Use EXACTLY the tool names from the schema above (e.g., 'python_exec' NOT 'python').
2. Use EXACTLY the parameter names from the schema (e.g., 'code' NOT 'filename').
3. Output valid JSON ONLY. NO COMMENTS inside JSON.

Correct tool usage:
```json
{{"tool": "...", "params": {{...}}}}
```"""

VERIFICATION_PROMPT = """Does this code work?
CODE: {code}
EXPECTED: {expected}
ACTUAL: {output}

Answer YES or NO."""

