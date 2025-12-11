# Tool Schema Loader - Loads schemas from JSON files
# Allows Memory Curator to update error_hints dynamically

import os
import json
from typing import Dict, Optional, List
from datetime import datetime

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class ToolSchemaLoader:
    """
    Loads and manages tool schemas from JSON files.
    
    Schemas are stored in tools/schemas/*.json
    Memory Curator Agent can update error_hints without touching code.
    """
    
    def __init__(self):
        self._schemas: Dict[str, dict] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all schemas from JSON files"""
        if not os.path.exists(SCHEMAS_DIR):
            os.makedirs(SCHEMAS_DIR, exist_ok=True)
            return
        
        for filename in os.listdir(SCHEMAS_DIR):
            if filename.endswith(".json"):
                tool_name = filename[:-5]  # Remove .json
                try:
                    with open(os.path.join(SCHEMAS_DIR, filename), 'r', encoding='utf-8') as f:
                        self._schemas[tool_name] = json.load(f)
                except Exception as e:
                    print(f"  ⚠️ Failed to load schema {filename}: {e}")
    
    def get_schema(self, tool_name: str) -> Optional[dict]:
        """Get schema for a tool"""
        return self._schemas.get(tool_name)
    
    def get_error_hints(self, tool_name: str) -> Dict[str, str]:
        """Get error hints for a tool"""
        schema = self._schemas.get(tool_name, {})
        return schema.get("error_hints", {})
    
    def get_hint_for_error(self, tool_name: str, error_type: str) -> Optional[str]:
        """Get specific hint for an error type"""
        hints = self.get_error_hints(tool_name)
        return hints.get(error_type)
    
    def add_error_hint(self, tool_name: str, error_type: str, hint: str) -> bool:
        """
        Add or update an error hint for a tool.
        Called by Memory Curator Agent when it learns a new error pattern.
        
        Returns True if successful.
        """
        if tool_name not in self._schemas:
            return False
        
        schema = self._schemas[tool_name]
        if "error_hints" not in schema:
            schema["error_hints"] = {}
        
        # Don't overwrite existing hints unless empty
        if error_type in schema["error_hints"] and schema["error_hints"][error_type]:
            return False  # Already has a hint
        
        schema["error_hints"][error_type] = hint
        schema["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        schema["version"] = schema.get("version", 1) + 1
        
        # Save to file
        return self._save_schema(tool_name, schema)
    
    def _save_schema(self, tool_name: str, schema: dict) -> bool:
        """Save schema to JSON file"""
        try:
            filepath = os.path.join(SCHEMAS_DIR, f"{tool_name}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"  ⚠️ Failed to save schema {tool_name}: {e}")
            return False
    
    def get_all_tool_names(self) -> List[str]:
        """Get list of all tools with schemas"""
        return list(self._schemas.keys())
    
    def get_schema_string(self, tool_name: str) -> str:
        """Get formatted schema string for prompt injection"""
        schema = self._schemas.get(tool_name)
        if not schema:
            return ""
        
        # Format parameters
        params_lines = []
        for param_name, param_info in schema.get("parameters", {}).items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            required = param_info.get("required", True)
            req_mark = "*" if required else ""
            params_lines.append(f"    - {param_name}{req_mark} ({param_type}): {param_desc}")
        params_str = "\n".join(params_lines) if params_lines else "    (none)"
        
        # Format examples
        examples = schema.get("examples", [])
        example_str = json.dumps(examples[0]) if examples else ""
        
        # Format error hints
        hints_str = ""
        hints = schema.get("error_hints", {})
        if hints:
            hints_lines = [f"    - {err}: {hint}" for err, hint in list(hints.items())[:3]]
            hints_str = f"\n  Error hints:\n" + "\n".join(hints_lines)
        
        return f"""{schema.get('name', tool_name)}:
  Description: {schema.get('description', '')}
  Parameters:
{params_str}
  Example: {example_str}{hints_str}"""
    
    def reload(self):
        """Reload all schemas from disk"""
        self._schemas.clear()
        self._load_all()


# Global instance
_loader: Optional[ToolSchemaLoader] = None


def get_schema_loader() -> ToolSchemaLoader:
    """Get or create global schema loader"""
    global _loader
    if _loader is None:
        _loader = ToolSchemaLoader()
    return _loader
