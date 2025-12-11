# Configuration - Self-Refine CLI with llama.cpp
# Optimized for Liquid LMF2 (small model)
# ============================================
# ALL configurable values should be HERE, not hardcoded elsewhere!

# ===================
# LLM Server
# ===================
import os
SERVER_URL = os.getenv("LLM_SERVER_URL", "http://localhost:8000/v1")  # Configurable for Docker

# ===================
# Model Parameters (LMF2 optimized)
# ===================
TEMPERATURE = 0.3           # Main generation temp (LMF2 recommends 0.3)
TEMPERATURE_FEEDBACK = 0.2  # Lower for evaluation/memory tasks
MAX_TOKENS = 4096

# ===================
# Poetiq Parallel Workers
# ===================
NUM_WORKERS = 2                 # Reduced to 2 for 8GB VRAM stability
WORKER_TEMPS = [0.2, 0.4]       # Temps for the 2 workers

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
# Optimized for 8GB VRAM: ~1.5GB model + 5 slots * 100MB = ~2.0GB total
LLM_PARALLEL_SLOTS = 5          # Total parallel slots in llama.cpp server

# Slot assignments (dedicated slots prevent collisions that cause GGML_ASSERT crash):
# ┌────────┬─────────────────────────────────────────────────────────────────┐
# │ Slot   │ Assignment                                                      │
# ├────────┼─────────────────────────────────────────────────────────────────┤
# │ 0      │ Worker 0 (parallel generation)                                  │
# │ 1      │ Worker 1 (parallel generation)                                  │
# │ 2      │ Memory ONLY (LLMLinker, Evolution, MemoryLearner, base.py)      │
# │ 3      │ Evaluator ONLY (pre-eval, _evaluate, _parallel_evaluate)        │
# │ 4      │ Task Generator ONLY (autonomous loop task generation)           │
# └────────┴─────────────────────────────────────────────────────────────────┘
#
# IMPORTANT: Each component has its own slot - NO SHARING = NO CRASHES
MEMORY_SLOT = 2                 # Dedicated: Memory system only
EVALUATOR_SLOT = 3              # Dedicated: Evaluator only  
TASK_GENERATOR_SLOT = 4         # Dedicated: Task generator only

MEMORY_CACHE_SIZE = 100         # Max cached LLM evaluations
MEMORY_MIN_IMPORTANCE = 5       # Min importance to retrieve
MAX_SESSIONS_SAVED = 100        # How many session logs to keep (increased from 10)
DEBUG_MEMORY = False            # Enable verbose memory logging (set True for debugging)

# ===================
# Agent Execution
# ===================
EXECUTION_TIMEOUT = 30          # Seconds for tool execution
AGENT_MAX_ITERATIONS = 10       # Max agentic loop iterations
AGENT_WORKSPACE = os.getenv("AGENT_WORKSPACE", "sandbox")     # Working directory

# ===================
# CONTEXT LIMITS (for LLM prompts)
# ===================
# These control how much data is passed to the LLM in various contexts.
# Higher values = more context = better quality (requires more VRAM)
# Lower values = faster but may lose important information
# Set these based on your GPU capacity. With dedicated GPU, use high values.

# --- Prompt Content Limits ---
LIMIT_TASK_PREVIEW = 500            # Task description in prompts (was 80-200)
LIMIT_RESPONSE_PREVIEW = 2000       # Response preview in prompts (was 200-600)
LIMIT_CODE_PREVIEW = 3000           # Code preview in prompts (was 200-300)
LIMIT_ERROR_PREVIEW = 500           # Error message preview (was 100-200)
LIMIT_FEEDBACK_PREVIEW = 1000       # Feedback text preview (was 300-400)
LIMIT_LESSON_PREVIEW = 500          # Lesson text preview (was 100)

# --- Memory System Limits ---
LIMIT_MEMORY_CANDIDATES = 25        # Max memory candidates to consider (was 15)
LIMIT_KEYWORDS_PER_MEMORY = 10      # Keywords extracted per memory (was 5)
LIMIT_KEYWORD_SOURCE_TEXT = 1000    # Text used for keyword extraction (was 300)

# --- Working Memory (File Indexing) ---
LIMIT_FILE_CHUNK_SIZE = 8000        # Max size per file chunk (was 4000-6000)
LIMIT_CHUNKS_PER_FILE = 20          # Max chunks per file (was 10)

# --- Learning System ---
LIMIT_PATTERN_TASK = 300            # Task preview for pattern learning (was 80)
LIMIT_PATTERN_RESPONSE = 1000       # Response preview for patterns (was 200-300)
LIMIT_ANALYSIS_TASK = 500           # Task preview for lesson analysis (was 150)

# --- Logging (these can stay lower, just for display) ---
LIMIT_LOG_TASK = 100                # Task in logs (display only)
LIMIT_LOG_RESPONSE = 500            # Response in logs (display only)
LIMIT_LOG_RESULT = 300              # Tool results in logs (display only)

# --- LLM Linker / Ranking ---
LLM_RANKING_THRESHOLD = 10          # Only use LLM ranking if more than N candidates

# --- Batch Learning ---
PATTERN_BATCH_SIZE = 5              # Learn patterns every N successful tasks
HIGH_SCORE_SKIP_THRESHOLD = 20      # Skip lesson LLM if score >= this
LOW_ITERATION_THRESHOLD = 1         # Skip lesson LLM if iterations <= this

# ===================
# Paths
# ===================
DATA_DIR = "data"           # Persistent: memories, graph, cache
OUTPUT_DIR = "outputs"      # Transient: logs, sessions
LOG_FILE = "outputs/refine_history.json"
