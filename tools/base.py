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
