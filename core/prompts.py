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

SCORING CRITERIA (be generous if the code works):
- 23-25: Perfect - tool used correctly, output clear, no issues
- 20-22: Excellent - minor style issues but functionally correct
- 17-19: Good - works but could be improved
- 14-16: Acceptable - partial solution
- 10-13: Weak - significant issues
- 0-9: Failed

IMPORTANT: If the code would execute and produce correct output, score AT LEAST 20.

You MUST output exactly this format at the end:
TOTAL_SCORE: [number]/25

Example: TOTAL_SCORE: 22/25"""

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


def build_tools_section(
    suggested_tools: list,
    registry,
    skills: list = None
) -> str:
    """
    Build tools section with two-phase approach:
    - Full schema for suggested tools (from ContextVectors)
    - Lightweight list for others
    - Lightweight list for harvested skills
    
    Args:
        suggested_tools: List of tool names to show full schema for
        registry: ToolRegistry instance
        skills: List of skill names (from SkillHarvester)
    
    Returns:
        Formatted tools section for prompt injection
    """
    # Phase 1: Full schemas for suggested tools
    full_schemas = []
    for tool_name in suggested_tools:
        schema = registry.get_full_schema(tool_name)
        if schema:
            full_schemas.append(schema)
    
    full_schemas_str = "\n\n".join(full_schemas) if full_schemas else "(none suggested)"
    
    # Phase 2: Lightweight list for other tools
    other_tools = registry.get_tools_summary(exclude=suggested_tools)
    
    # Phase 3: Skills (always lightweight - just function signatures)
    skills_str = ""
    if skills:
        skills_str = "\n".join([f"- {s}" for s in skills[:10]])  # Limit to 10
    else:
        skills_str = "(none yet)"
    
    return f"""## RECOMMENDED TOOLS (full schema):
{full_schemas_str}

## OTHER AVAILABLE TOOLS (request schema if needed):
{other_tools}

## HARVESTED SKILLS (reusable functions):
{skills_str}

To request full schema: {{"get_schema": "tool_name"}}
To use a tool: {{"tool": "tool_name", "params": {{...}}}}"""
