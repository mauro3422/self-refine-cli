# Configuration - Self-Refine CLI with llama.cpp
# Optimized for Liquid LMF2 (small model)
# ============================================
# ALL configurable values should be HERE, not hardcoded elsewhere!

# ===================
# LLM Server
# ===================
SERVER_URL = "http://localhost:8000/v1"  # Local llama.cpp server

# ===================
# Model Parameters (LMF2 optimized)
# ===================
TEMPERATURE = 0.3           # Main generation temp (LMF2 recommends 0.3)
TEMPERATURE_FEEDBACK = 0.2  # Lower for evaluation/memory tasks
MAX_TOKENS = 4096

# ===================
# Poetiq Parallel Workers
# ===================
NUM_WORKERS = 3
WORKER_TEMPS = [0.2, 0.3, 0.4]  # Lower temps = less hallucination

# ===================
# Self-Refine Loop
# ===================
MAX_ITERATIONS = 3          # Max refinement iterations (reduced for speed)
SCORE_THRESHOLD = 18        # Stop if score >= this (more achievable)
FEEDBACK_DIMENSIONS = 5     # Evaluation dimensions

# ===================
# Autonomous Loop
# ===================
AUTO_SLEEP_INTERVAL = 5         # Seconds between tasks
AUTO_HEALTH_CHECK_EVERY = 10    # Check health every N tasks
AUTO_MAX_CONSECUTIVE_FAIL = 3   # Trigger restart after N failures
AUTO_SUCCESS_SCORE = 10         # Score >= this = partial success

# ===================
# Memory System
# ===================
MEMORY_SLOT = 3                 # Dedicated slot for LLMLinker/Evolution (keeps context warm)
MEMORY_CACHE_SIZE = 100         # Max cached LLM evaluations
MEMORY_MIN_IMPORTANCE = 5       # Min importance to retrieve
MAX_SESSIONS_SAVED = 10         # How many session logs to keep

# ===================
# Agent Execution
# ===================
EXECUTION_TIMEOUT = 30          # Seconds for tool execution
AGENT_MAX_ITERATIONS = 10       # Max agentic loop iterations
AGENT_WORKSPACE = "sandbox"     # Working directory

# ===================
# Paths
# ===================
DATA_DIR = "data"           # Persistent: memories, graph, cache
OUTPUT_DIR = "outputs"      # Transient: logs, sessions
LOG_FILE = "outputs/refine_history.json"

