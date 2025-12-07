# Configuration - Self-Refine CLI with llama.cpp

# llama.cpp Server
SERVER_URL = "http://localhost:8000/v1"  # Local llama.cpp server

# Model Parameters
TEMPERATURE = 0.7
TEMPERATURE_FEEDBACK = 0.3
MAX_TOKENS = 4096

# Poetiq Parameters
NUM_WORKERS = 3          # Default parallel workers
WORKER_TEMPS = [0.5, 0.7, 0.9]  # Temperatures for diversity

# Self-Refine Parameters
MAX_ITERATIONS = 5
SCORE_THRESHOLD = 22
FEEDBACK_DIMENSIONS = 5

# Execution Safety
EXECUTION_TIMEOUT = 30

# Paths
OUTPUT_DIR = "outputs"
LOG_FILE = "outputs/refine_history.json"
AGENT_MAX_ITERATIONS = 10
AGENT_WORKSPACE = "sandbox"
