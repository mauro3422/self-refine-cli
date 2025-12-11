# Base Tool class for all tools
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class Tool(ABC):
    """Base class for all agent tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        JSON Schema for tool parameters.
        Example:
        {
            "path": {
                "type": "string",
                "description": "Path to the file"
            }
        }
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        Returns: {"success": bool, "result": Any, "error": Optional[str]}
        """
        pass
    
    @property
    def error_hints(self) -> Dict[str, str]:
        """
        Optional error hints for common errors with this tool.
        Override in subclasses to provide tool-specific guidance.
        Example: {"FileNotFoundError": "Check that the path exists"}
        """
        return {}
    
    def get_schema_string(self, example: str = "") -> str:
        """
        Get full schema as formatted string for prompt injection.
        Includes: name, description, parameters, example, and error hints.
        """
        import json
        
        # Format parameters
        params_lines = []
        for param_name, param_info in self.parameters.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            required = param_info.get("required", True)
            req_mark = "*" if required else ""
            params_lines.append(f"    - {param_name}{req_mark} ({param_type}): {param_desc}")
        params_str = "\n".join(params_lines) if params_lines else "    (none)"
        
        # Format error hints if any
        hints_str = ""
        if self.error_hints:
            hints_lines = [f"    - {err}: {hint}" for err, hint in self.error_hints.items()]
            hints_str = f"\n  Error hints:\n" + "\n".join(hints_lines)
        
        return f"""{self.name}:
  Description: {self.description}
  Parameters:
{params_str}
  Example: {example}{hints_str}"""
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys())
                }
            }
        }
    
    def __repr__(self) -> str:
        return f"Tool({self.name})"
