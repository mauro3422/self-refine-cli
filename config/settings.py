# URLs, parámetros del modelo, paths - Self-Refine Configuration

# LM Studio API Configuration
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "lfm2"

# Self-Refine Parameters
MAX_ITERATIONS = 5          # Maximum refinement iterations
SCORE_THRESHOLD = 23        # Stop if score >= this (out of 25)
FEEDBACK_DIMENSIONS = 5     # Number of evaluation dimensions

# Model Parameters - INCREASED FOR LFM2
TEMPERATURE = 0.7           # Generation temperature
TEMPERATURE_FEEDBACK = 0.3  # Lower temp for more consistent evaluation
MAX_TOKENS = 16000          # Increased for longer outputs (model has 128k context)

# Execution Safety
EXECUTION_TIMEOUT = 30      # Increased to 30s for longer operations

# Output Configuration
OUTPUT_DIR = "outputs"
LOG_FILE = "outputs/refine_history.json"

# Agent Configuration
AGENT_MAX_ITERATIONS = 10   # Max tool use iterations
AGENT_WORKSPACE = "sandbox" # Agent's workspace folder
