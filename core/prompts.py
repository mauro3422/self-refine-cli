# Prompts Module - Now uses YAML hot-reload system
# Edit prompts/*.yaml files to modify prompts without code changes
#
# This file provides backward compatibility - imports from YAML files
# For direct YAML access use: from prompts import get_prompt

from prompts import get_prompt

# === BACKWARD COMPATIBILITY LAYER ===
# These variables load from YAML on first access
# They support hot-reload when YAML files are modified

def _get_agent_system_prompt():
    return get_prompt("agent", "system_prompt")

def _get_eval_prompt():
    return get_prompt("evaluation", "eval_prompt")

def _get_refine_prompt():
    return get_prompt("agent", "refine_prompt")

def _get_verification_prompt():
    return get_prompt("evaluation", "verify_prompt")


# For backward compatibility, expose as module-level strings
# These are loaded once on import but the YAML loader handles hot-reload internally
AGENT_SYSTEM_PROMPT = get_prompt("agent", "system_prompt")
EVAL_PROMPT = get_prompt("evaluation", "eval_prompt")
REFINE_PROMPT = get_prompt("agent", "refine_prompt")
VERIFICATION_PROMPT = get_prompt("evaluation", "verify_prompt")


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
