# LLM Client - llama.cpp Server with Slot Affinity
# Uses native llama.cpp API for slot control + OpenAI-compatible for simple requests

import time
import requests
from openai import OpenAI
from config.settings import SERVER_URL, TEMPERATURE, MAX_TOKENS


class LLMClient:
    """
    Client for llama.cpp server with SLOT AFFINITY support.
    
    Slot affinity prevents context thrashing by assigning workers to dedicated slots.
    - Worker 0 → Slot 0
    - Worker 1 → Slot 1
    - Worker 2 → Slot 2
    
    When slot_id is specified, uses native /completion API.
    When slot_id is -1 (default), uses OpenAI-compatible API.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1  # seconds, will double each retry
    
    def __init__(self):
        self.client = OpenAI(
            base_url=SERVER_URL,
            api_key="not-needed"
        )
        # Native API base URL (without /v1)
        self.native_url = SERVER_URL.replace("/v1", "")
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
    
    def chat(self, messages: list, temp: float = TEMPERATURE, slot_id: int = -1) -> str:
        """
        Send chat request to llama.cpp server with automatic retry on failure.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temp: Temperature for generation
            slot_id: If >= 0, use native API with specific slot. If -1, use OpenAI API (auto-assign).
        """
        if slot_id >= 0:
            return self._chat_with_slot(messages, temp, slot_id)
        else:
            return self._chat_openai(messages, temp)
    
    def _chat_openai(self, messages: list, temp: float) -> str:
        """Use OpenAI-compatible API (no slot control)"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model="local-model",
                    messages=messages,
                    temperature=temp,
                    max_tokens=MAX_TOKENS,
                    frequency_penalty=0.5,  # Discourage repetition loops
                    presence_penalty=0.5,   # Encourage new topics
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
    
    def _chat_with_slot(self, messages: list, temp: float, slot_id: int) -> str:
        """
        Use native llama.cpp /completion API with specific slot.
        This prevents context thrashing by keeping worker-slot affinity.
        """
        # Convert messages to single prompt (llama.cpp native format)
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "prompt": prompt,
            "temperature": temp,
            "n_predict": MAX_TOKENS,
            "id_slot": slot_id,  # KEY: Assign to specific slot!
            "cache_prompt": True,  # Default to True, but disable for sensitive slots below
            "repeat_penalty": 1.1,  # Standard repetition penalty
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5,
            "stop": ["</s>", "[INST]", "[/INST]", "User:", "Human:"],
        }
        
        # CRITICAL STABILITY FIX:
        # Slots >= 3 (Memory, Evaluator, TaskGen) process highly variable prompts.
        # Reusing context often fails to truncate correctly in llama.cpp, causing GGML_ASSERT crash.
        # STARTING with cache_prompt=False forces a clean slot reset every time.
        if slot_id >= 3:
            payload["cache_prompt"] = False
            time.sleep(0.2)  # Small safety delay for slot release
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                # On retry, disable cache to force slot reset (prevents GGML_ASSERT crash)
                if attempt > 0:
                    payload["cache_prompt"] = False
                    time.sleep(0.5)  # Small delay to let slot fully reset
                
                response = requests.post(
                    f"{self.native_url}/completion",
                    json=payload,
                    timeout=300  # 5 min timeout for long generations
                )
                
                if response.status_code == 200:
                    self.consecutive_errors = 0
                    result = response.json()
                    return result.get("content", "")
                elif response.status_code == 503:
                    # Server busy - wait and retry
                    raise Exception(f"Server busy (503) - slot {slot_id} may be in use")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")
                    
            except requests.exceptions.ConnectionError as e:
                # Server crashed or unreachable
                last_error = e
                self.consecutive_errors += 1
                print(f"    🔴 LLM SERVER DOWN (slot {slot_id}): {str(e)[:50]}")
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt) * 2  # Longer delay for crashes
                    print(f"    ⏳ Waiting {delay}s before retry...")
                    time.sleep(delay)
                    
            except Exception as e:
                last_error = e
                self.consecutive_errors += 1
                
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    print(f"    ⚠️ LLM slot {slot_id} error (attempt {attempt+1}): {str(e)[:50]}... Retrying in {delay}s")
                    time.sleep(delay)
        
        print(f"    ❌ LLM slot {slot_id} failed after {self.MAX_RETRIES} attempts. Last error: {last_error}")
        return f"ERROR: Connection error on slot {slot_id}."
    
    def _messages_to_prompt(self, messages: list) -> str:
        """Convert OpenAI-style messages to llama.cpp prompt format"""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"[INST] <<SYS>>\n{content}\n<</SYS>>\n")
            elif role == "user":
                prompt_parts.append(f"[INST] {content} [/INST]\n")
            elif role == "assistant":
                prompt_parts.append(f"{content}\n")
        
        return "".join(prompt_parts)
    
    def generate(self, prompt: str, temp: float = TEMPERATURE, slot_id: int = -1) -> str:
        """Simple wrapper for single prompt"""
        return self.chat([{"role": "user", "content": prompt}], temp, slot_id)
    
    def needs_restart(self) -> bool:
        """Check if server likely needs restart based on error patterns"""
        return self.consecutive_errors >= 5  # 5+ consecutive failures = bad
