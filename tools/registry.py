# Tool Registry - manages available tools with schema discovery
from typing import Dict, List, Any, Optional
from tools.base import Tool


class ToolRegistry:
    """Registry for managing and discovering tools"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Tool] = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool
        print(f"  📦 Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_tool_names_brief(self) -> str:
        """Get just tool names with one-line descriptions (for system prompt)"""
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description[:60]}...")
        return "\n".join(lines)

    def get_tools_prompt(self) -> str:
        """Get detailed tool definitions with examples for system prompt"""
        lines = []
        for name in self._tools:
            schema = self.get_tool_schema(name)
            params = ", ".join([f"{k}: {v['type']}" for k, v in schema['parameters'].items()])
            example = schema.get('example', '')
            lines.append(f"### {name}({params})\n   Description: {schema['description']}\n   Example: {example}\n")
        return "\n".join(lines)
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for a specific tool"""
        tool = self.get(name)
        if not tool:
            return None
        
        schema = {
            "name": tool.name,
            "description": tool.description,
            "parameters": {},
            "example": ""
        }
        
        for param_name, param_info in tool.parameters.items():
            schema["parameters"][param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", ""),
                "required": param_info.get("required", False)
            }
        
        # Add example for EVERY tool (critical for LLM to understand usage)
        examples = {
            "write_file": '{"tool": "write_file", "params": {"path": "sandbox/file.py", "content": "def foo(): pass"}}',
            "read_file": '{"tool": "read_file", "params": {"path": "sandbox/file.py"}}',
            "list_dir": '{"tool": "list_dir", "params": {"path": "sandbox/"}}',
            "python_exec": '{"tool": "python_exec", "params": {"code": "print(2+2)"}}',
            "run_command": '{"tool": "run_command", "params": {"command": "dir"}}',
            "search_files": '{"tool": "search_files", "params": {"query": "def main", "path": "sandbox/", "extensions": ".py"}}',
            "analyze_code_structure": '{"tool": "analyze_code_structure", "params": {"path": "sandbox/main.py"}}',
            "replace_in_file": '{"tool": "replace_in_file", "params": {"path": "sandbox/file.py", "target": "old_text", "replacement": "new_text"}}',
            "apply_patch": '{"tool": "apply_patch", "params": {"path": "sandbox/file.py", "original_block": "def old():", "new_block": "def new():"}}',
            "linter": '{"tool": "linter", "params": {"path": "sandbox/script.py"}}',
            "run_tests": '{"tool": "run_tests", "params": {"path": "sandbox/test_module.py"}}'
        }
        schema["example"] = examples.get(name, "")
        
        return schema
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all tools in function calling format"""
        return [tool.to_function_schema() for tool in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """Get human-readable description of all tools"""
        lines = ["Available tools:"]
        for name, tool in self._tools.items():
            params = ", ".join(tool.parameters.keys())
            lines.append(f"  - {name}({params}): {tool.description}")
        return "\n".join(lines)
    
    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name, filtering to only valid parameters"""
        tool = self.get(name)
        if not tool:
            # NEW: Smart suggestions for hallucinated tools
            available = self.list_tools()
            
            # Find similar tool names (simple fuzzy match)
            similar = []
            name_lower = name.lower()
            for t in available:
                # Check if any part of the name matches
                if any(word in t.lower() for word in name_lower.split('_')):
                    similar.append(t)
                elif any(word in name_lower for word in t.lower().split('_')):
                    similar.append(t)
            
            suggestion = ""
            if similar:
                suggestion = f" Did you mean: {', '.join(similar[:3])}?"
            else:
                suggestion = f" Available tools: {', '.join(available)}"
            
            return {
                "success": False, 
                "error": f"Tool '{name}' not found.{suggestion}",
                "available_tools": available  # Include for learning
            }
        
        try:
            # Filter kwargs to only include valid parameters for this tool
            valid_params = tool.parameters.keys()
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
            
            return tool.execute(**filtered_kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global registry instance
registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry"""
    return registry

