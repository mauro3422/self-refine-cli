# 🧠 Self-Refine CLI — Autonomous Self-Improving Agent

<div align="center">

**A fully autonomous, self-improving AI agent that generates code, verifies it, learns from mistakes, and continuously upgrades its own capabilities.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![llama.cpp](https://img.shields.io/badge/inference-llama.cpp-green.svg)](https://github.com/ggerganov/llama.cpp)
[![Local Hardware](https://img.shields.io/badge/runs%20on-local%20GPU-orange.svg)](#requirements)

</div>

> ⚠️ **100% LOCAL** — Runs entirely on your machine using llama.cpp with Vulkan GPU acceleration. No paid APIs (OpenAI, Anthropic, Google). Perfect for AI experimentation on your own hardware.

---

## 🎯 What This Project Does

This is not just another LLM wrapper. **Self-Refine CLI** is an autonomous agent that:

1. **Generates coding tasks** for itself with adaptive difficulty
2. **Spawns 3 parallel workers** that each generate, execute, and verify code
3. **Selects the best verified solution** from workers
4. **Iteratively refines** the solution using self-feedback
5. **Learns lessons** from successes and failures into long-term memory
6. **Harvests skills** — verified functions become reusable for future tasks
7. **Adjusts difficulty** — curriculum learning based on performance history

The result: an agent that **improves itself over time** without human intervention.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AUTONOMOUS LOOP                               │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐        │
│  │ Task Generator │───▶│ PoetiqRunner   │───▶│ Result Logger  │        │
│  │ (Adaptive Diff)│    │                │    │ + Learner      │        │
│  └────────────────┘    └────────┬───────┘    └────────────────┘        │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌─────────────────────┐    ┌─────────────────────┐
        │   POETIQ PIPELINE   │    │   MEMORY SYSTEM     │
        │                     │    │                     │
        │ ┌─────┐ ┌─────┐    │    │  SmartMemory        │
        │ │ W1  │ │ W2  │    │    │  ContextVectors     │
        │ └──┬──┘ └──┬──┘    │    │  MemoryGraph        │
        │    │       │       │    │  WorkingMemory      │
        │ ┌──┴───────┴──┐    │    │  SkillHarvester     │
        │ │  Aggregator │    │    │  TestPatterns       │
        │ └──────┬──────┘    │    │  ReflectionBuffer   │
        │        ▼           │    │                     │
        │ ┌─────────────┐    │    └─────────────────────┘
        │ │ SelfRefiner │    │
        │ └─────────────┘    │
        └────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **GPU with Vulkan support** (tested on AMD RX 6600, NVIDIA works too)
- **16GB+ RAM** recommended
- **[llama.cpp server](https://github.com/ggerganov/llama.cpp)** running locally

### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/mauro3422/self-refine-cli.git
cd self-refine-cli

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Download & Start LLM Server

```bash
# Download a model (example: Qwen2.5-Coder-7B)
# Place in models/ folder

# Start llama.cpp server with Vulkan GPU acceleration
# Windows:
scripts\start_llm.bat

# Linux/Mac:
# ./llama.cpp/build/bin/llama-server -m models/your-model.gguf -c 32768 --port 8080
```

### 3. Run the Agent

```bash
# Autonomous mode - let the agent teach itself
python autonomous_loop.py

# Interactive mode - give tasks directly
python main.py

# Single task with Poetiq pipeline
python run_test.py "create a function that reverses a string" --poetiq
```

### 4. Monitor (Optional)

```bash
# Launch web dashboard at http://localhost:5000
python -m ui.dashboard
```


---

## 📁 Project Structure

```
self-refine-cli/
├── autonomous_loop.py       # 🔄 Main autonomous self-improvement loop
├── main.py                  # 🖥️ Interactive CLI entry point
│
├── core/                    # ⚙️ Core Modules
│   ├── poetiq/              # Poetiq Pipeline
│   │   ├── runner.py        #   └─ Orchestrates workers → aggregator → refiner
│   │   ├── worker.py        #   └─ True Poetiq: generate + execute + verify
│   │   ├── aggregator.py    #   └─ Selects best verified response
│   │   └── refiner.py       #   └─ Self-refine loop with feedback
│   ├── llm_client.py        # LLM communication (OpenAI-compatible)
│   ├── code_verifier.py     # Execute code against test cases
│   ├── agentic_loop.py      # Multi-tool execution loop
│   ├── parsers.py           # Extract tool calls, scores, code
│   └── prompts.py           # Centralized system prompts
│
├── memory/                  # 🧠 Memory System (7 subsystems)
│   ├── orchestrator.py      # Central hub coordinating all memory
│   ├── base.py              # SmartMemory: long-term with decay + ranking
│   ├── context_vectors.py   # Category detection + tool suggestions
│   ├── llm_linker.py        # Intelligent memory ranking
│   ├── graph.py             # NetworkX graph with PageRank
│   ├── working_memory.py    # Project file indexing (ChromaDB)
│   ├── evolution.py         # Merge/evolve memories
│   ├── reflection_buffer.py # Intra-session error avoidance
│   ├── learner.py           # Extract lessons from sessions
│   ├── skill_harvester.py   # Save verified functions as skills
│   ├── test_patterns.py     # Learn successful test patterns
│   ├── adaptive_difficulty.py # Curriculum learning (1-5)
│   ├── cache.py             # LRU embedding cache
│   ├── vector_store.py      # ChromaDB vector storage
│   └── persistence.py       # Export/import memory state
│
├── tools/                   # 🔧 Agent Tools
│   ├── registry.py          # Singleton tool registry
│   ├── file_tools.py        # read_file, write_file, list_dir
│   ├── code_tools.py        # python_exec
│   ├── edit_tools.py        # replace_in_file, apply_patch
│   ├── search_tools.py      # search_files
│   ├── command_tools.py     # run_command
│   └── verify_tools.py      # linter, run_tests
│
├── config/                  # ⚙️ Configuration
│   └── settings.py          # All centralized settings
│
├── data/                    # 💾 Persistent Data
│   ├── agent_memory.json    # Long-term memories
│   ├── memory_graph.json    # Memory relationships
│   ├── skills/              # Harvested skills library
│   └── test_patterns/       # Learned test patterns
│
├── sandbox/                 # 📦 Secure Execution Environment
└── output/                  # 📊 Logs and Session Data
```

---

## 🧠 Memory System Deep Dive

The memory system is inspired by **A-Mem** (Agentic Memory) and **DreamCoder**. It enables the agent to:

### 1. SmartMemory — Long-Term Lessons
```python
# Memories have:
# - Temporal decay (0.98/day) — old unused memories fade
# - Importance scoring (1-10) — critical lessons persist
# - Success/failure tracking — learns what works
# - Weighted links to related memories
```

### 2. ContextVectors — Category Detection
```python
# Detects task type from keywords:
CATEGORIES = ["file_create", "file_read", "code_exec", "analysis", ...]

# Suggests relevant tools:
"file_create" → ["write_file", "python_exec"]
```

### 3. InContextVectors (ICV) — Dynamic Tips
```python
# Category-specific guidance injected into prompts:
"code_exec" → "Always include error handling. Test edge cases."
```

### 4. MemoryGraph — Relational Knowledge
```python
# NetworkX graph connecting related memories
# Uses PageRank to identify central/important memories
# Strengthens links on co-retrieval, weakens on contradictions
```

### 5. WorkingMemory — Project Context
```python
# Indexes current project files using ChromaDB
# Chunks Python files by function/class for precise retrieval
# Provides relevant code snippets for the current task
```

### 6. SkillHarvester — Reusable Functions
```python
# Extracts verified functions from successful code
# Saves as skills in skills/ directory
# Injects available skills into future prompts
```

### 7. ReflectionBuffer — Session Learning
```python
# Captures errors and lessons within a session
# Prevents repeating the same mistakes in refinement iterations
# Auto-generates lessons from common error types
```

---

## ⚡ Poetiq Pipeline Deep Dive

The Poetiq system implements **True Poetiq** — each worker:

### Phase 1: Parallel Generation
```
┌─────────────────────────────────────────────────┐
│                PoetiqRunner                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │Worker 0 │  │Worker 1 │  │Worker 2 │         │
│  │ t=0.3   │  │ t=0.5   │  │ t=0.7   │ ← Varied│
│  └────┬────┘  └────┬────┘  └────┬────┘   temps │
│       │            │            │               │
│  [Generate Code]   [Generate]   [Generate]      │
│       │            │            │               │
│  [Execute & Verify][Execute]   [Execute]        │
│       │            │            │               │
│  [verified=True]  [verified=?] [verified=?]     │
│       └────────────┼────────────┘               │
│                    ▼                            │
│            ┌──────────────┐                     │
│            │  Aggregator  │ ← Prioritizes       │
│            │              │   verified workers  │
│            └──────────────┘                     │
└─────────────────────────────────────────────────┘
```

### Phase 2: Self-Refine Loop
```
┌─────────────────────────────────────────────────┐
│              SelfRefiner                         │
│                                                  │
│  ┌──────────┐   score < 18?   ┌─────────────┐  │
│  │ Evaluate │ ───────────────▶│   Refine    │  │
│  │ (1 call) │                 │ (1 worker)  │  │
│  └──────────┘                 └──────┬──────┘  │
│       ▲                              │          │
│       └──────────────────────────────┘          │
│                  (max 3 iterations)             │
└─────────────────────────────────────────────────┘
```

---

## 📈 Adaptive Difficulty (Curriculum Learning)

The agent automatically adjusts task difficulty based on performance:

| Level | Name | Examples |
|-------|------|----------|
| 1 | Basic | reverse string, sum list, check even |
| 2 | Easy | count vowels, find max, remove duplicates |
| 3 | Medium | validate email, parse date, word frequency |
| 4 | Hard | merge intervals, balanced brackets, LRU cache |
| 5 | Expert | regex parser, expression evaluator, graph algorithms |

**Rules:**
- ≥75% success rate → **Level Up** 📈
- <40% success rate → **Level Down** 📉
- 30% chance to target weak categories

---

## 🔧 Configuration

All settings are centralized in `config/settings.py`:

```python
# LLM Config
LLM_BASE_URL = "http://127.0.0.1:8080/v1"
LLM_MODEL = "local-model"
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.3

# Poetiq Config
POETIQ_NUM_WORKERS = 3
WORKER_TEMPS = [0.3, 0.5, 0.7]  # Diversity through temperature

# Self-Refine
REFINE_MAX_ITERATIONS = 3
REFINE_THRESHOLD = 18  # Score 0-25

# Memory
MEMORY_DECAY_FACTOR = 0.98
TOP_K_MEMORIES = 5

# And many more...
```

---

## 📊 LLM Call Efficiency

The system is optimized to minimize LLM calls:

| Phase | Calls | Notes |
|-------|-------|-------|
| Task Generation | 1 | Autonomous loop only |
| Workers (×3) | 3-9 | 1 each, +retry if verify fails |
| Pre-Eval | 0-1 | **Skipped if all verified** ✅ |
| Refine (×3 iter) | 3-6 | 1 eval + 1 refine per iter |
| Lesson Extract | 0-1 | **Skipped if high score** ✅ |
| **Total** | **~6-15** | (was ~30 before optimizations) |

---

## 🧪 Running Tests

```bash
# Single task with Poetiq
python run_test.py "create a fibonacci function" --poetiq

# Stress test with multiple workers
python run_test.py --stress 6

# Run autonomous loop
python autonomous_loop.py
```

---

## 📜 Research & Inspiration

### Core Papers
| Paper | Contribution |
|-------|--------------|
| [Self-Refine](https://arxiv.org/abs/2303.17651) | Iterative refinement with self-feedback |
| [A-Mem](https://arxiv.org/abs/2502.12110) | Agentic memory with evolution & decay |
| [DreamCoder](https://arxiv.org/abs/2006.08381) | Program synthesis + skill library |

### Poetiq Architecture
- [Poetiq ARC-AGI Solver](https://github.com/poetiq-ai/poetiq-arc-agi-solver)
- [Traversing the Frontier](https://poetiq.ai/posts/arcagi_announcement/)
- [Shatters ARC-AGI-2](https://poetiq.ai/posts/arcagi_verified/)

### Tools
- [llama.cpp](https://github.com/ggerganov/llama.cpp) — Local inference server
- [ChromaDB](https://www.trychroma.com/) — Vector storage for memory

---

## 🔒 Security

All file operations are sandboxed:
- Tools can only read/write within `sandbox/` directory
- Path traversal attacks are blocked
- Code execution is isolated

---

## 📋 Requirements

**Python Packages** (see `requirements.txt`):
```
requests>=2.28.0
openai>=1.0.0
chromadb>=0.4.0
pandas>=2.0.0
numpy>=1.24.0
networkx>=3.0
flask>=2.3.0
```

**Hardware:**
- GPU with Vulkan/CUDA support (tested on AMD RX 6600)
- 16GB+ RAM recommended
- 50GB+ disk space for models

**LLM Server:**
- [llama.cpp](https://github.com/ggerganov/llama.cpp) compiled with Vulkan/CUDA
- Recommended model: Qwen2.5-Coder-7B-Instruct (Q4_K_M or Q5_K_M)

**Troubleshooting:**
- If ChromaDB fails: `pip install chromadb --upgrade`
- If GPU not detected: Check Vulkan/CUDA drivers
- If port 8080 busy: Change port in `config/settings.py`

---

## 🤝 Contributing

Contributions welcome! Key areas:
- New tools for the agent
- Memory system improvements
- Performance optimizations
- Documentation

---

## 📄 License

MIT License — Use freely, learn boldly.

---

<div align="center">

**Built for self-improvement. By an agent, for agents (and curious humans).**

</div>
