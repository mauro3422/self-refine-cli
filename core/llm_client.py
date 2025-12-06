# Cliente para LM Studio API

import requests
from typing import List, Dict
from config.settings import LM_STUDIO_URL, MODEL_NAME, TEMPERATURE, MAX_TOKENS


class LLMClient:
    def __init__(self):
        self.url = LM_STUDIO_URL
        self.model = MODEL_NAME
    
    def chat(self, messages: List[Dict[str, str]], temp: float = TEMPERATURE) -> str:
        """Llama a LM Studio API"""
        try:
            resp = requests.post(self.url, json={
                "model": self.model,
                "messages": messages,
                "temperature": temp,
                "max_tokens": MAX_TOKENS
            }, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.ConnectionError:
            return "ERROR: LM Studio no está corriendo en localhost:1234"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def generate(self, prompt: str, temp: float = TEMPERATURE) -> str:
        """Wrapper simple para single prompt"""
        return self.chat([{"role": "user", "content": prompt}], temp)
