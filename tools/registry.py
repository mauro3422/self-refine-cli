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
        
        # Add example based on tool type
        if name == "write_file":
            schema["example"] = '{"tool": "write_file", "params": {"path": "sandbox/file.py", "content": "def foo(): pass"}}'
        elif name == "read_file":
            schema["example"] = '{"tool": "read_file", "params": {"path": "sandbox/file.py"}}'
        elif name == "list_dir":
            schema["example"] = '{"tool": "list_dir", "params": {"path": "sandbox/"}}'
        elif name == "python_exec":
            schema["example"] = '{"tool": "python_exec", "params": {"code": "print(2+2)"}}'
        elif name == "run_command":
            schema["example"] = '{"tool": "run_command", "params": {"command": "ls -la"}}'
        
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
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global registry instance
registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry"""
    return registry

