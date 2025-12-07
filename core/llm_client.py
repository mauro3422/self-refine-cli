# LLM Client - llama.cpp Server Only
# Uses OpenAI-compatible API on local server

from openai import OpenAI
from config.settings import SERVER_URL, TEMPERATURE, MAX_TOKENS


class LLMClient:
    """Client for llama.cpp server via OpenAI protocol"""
    
    def __init__(self):
        self.client = OpenAI(
            base_url=SERVER_URL,
            api_key="not-needed"
        )
    
    def chat(self, messages: list, temp: float = TEMPERATURE) -> str:
        """Send chat request to llama.cpp server"""
        try:
            response = self.client.chat.completions.create(
                model="local-model",
                messages=messages,
                temperature=temp,
                max_tokens=MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def generate(self, prompt: str, temp: float = TEMPERATURE) -> str:
        """Simple wrapper for single prompt"""
        return self.chat([{"role": "user", "content": prompt}], temp)
