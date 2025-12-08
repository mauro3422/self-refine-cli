# LLM Client - llama.cpp Server Only
# Uses OpenAI-compatible API on local server

import time
from openai import OpenAI
from config.settings import SERVER_URL, TEMPERATURE, MAX_TOKENS


class LLMClient:
    """Client for llama.cpp server via OpenAI protocol"""
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1  # seconds, will double each retry
    
    def __init__(self):
        self.client = OpenAI(
            base_url=SERVER_URL,
            api_key="not-needed"
        )
        self.consecutive_errors = 0  # Track health
    
    def health_check(self) -> dict:
        """Check if server is responsive. Returns {healthy: bool, latency_ms: float, error: str}"""
        start = time.time()
        try:
            # Simple ping with tiny prompt
            response = self.client.chat.completions.create(
                model="local-model",
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=5,
            )
            latency = (time.time() - start) * 1000
            self.consecutive_errors = 0
            return {"healthy": True, "latency_ms": latency, "error": None}
        except Exception as e:
            self.consecutive_errors += 1
            return {"healthy": False, "latency_ms": None, "error": str(e)}
    
    def chat(self, messages: list, temp: float = TEMPERATURE) -> str:
        """Send chat request to llama.cpp server with automatic retry on failure"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model="local-model",
                    messages=messages,
                    temperature=temp,
                    max_tokens=MAX_TOKENS,
                )
                self.consecutive_errors = 0  # Reset on success
                return response.choices[0].message.content
                
            except Exception as e:
                last_error = e
                self.consecutive_errors += 1
                
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)  # 1s, 2s, 4s
                    print(f"    ⚠️ LLM error (attempt {attempt+1}/{self.MAX_RETRIES}): {str(e)[:50]}... Retrying in {delay}s")
                    time.sleep(delay)
        
        # All retries failed
        print(f"    ❌ LLM failed after {self.MAX_RETRIES} attempts. Last error: {last_error}")
        return f"ERROR: Connection error. Server may be overloaded or down."
    
    def generate(self, prompt: str, temp: float = TEMPERATURE) -> str:
        """Simple wrapper for single prompt"""
        return self.chat([{"role": "user", "content": prompt}], temp)
    
    def needs_restart(self) -> bool:
        """Check if server likely needs restart based on error patterns"""
        return self.consecutive_errors >= 5  # 5+ consecutive failures = bad

