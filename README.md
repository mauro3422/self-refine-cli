# Self-Refine CLI with Poetiq Parallel System

A self-refining AI agent powered by **llama.cpp** with true parallel inference on GPU.

## 🚀 Quick Start

```bash
# 1. Start the llama.cpp server (GPU)
start_server.bat

# 2. Run agent
python run_test.py "your task" --poetiq
```

## 🏗️ Architecture

```
           ┌──────────────────┐
           │   PoetiqRunner   │  ← Orchestrator
           └────────┬─────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Worker 0 │   │Worker 1 │   │Worker 2 │  ← 1 LLM call each (PARALLEL)
└────┬────┘   └────┬────┘   └────┬────┘
     └─────────────┼─────────────┘
                   ▼
           ┌──────────────┐
           │ VotingSystem │  ← Pick best response
           └──────┬───────┘
                  ▼
           ┌──────────────┐
           │ ToolExecutor │  ← Execute winner's tool
           └──────────────┘
```

## 📁 Project Structure

```
self-refine-cli/
├── core/                    # Core modules
│   ├── llm_client.py       # llama.cpp client
│   ├── poetiq.py           # Parallel workers system
│   ├── agent.py            # Full self-refine agent
│   ├── parsers.py          # Tool call extraction
│   ├── prompts.py          # System prompts
│   ├── evaluator.py        # Response evaluation
│   └── verification.py     # Code verification
├── tools/                   # Agent tools
│   ├── file_tools.py       # read_file, write_file, list_dir
│   └── command_tools.py    # python_exec, run_command
├── config/
│   └── settings.py         # Configuration
├── server/                  # llama.cpp binaries
├── sandbox/                 # Agent workspace
├── run_test.py             # Test runner
├── start_server.bat        # Start GPU server
└── stop_server.bat         # Stop server
```

## ⚡ Server Configuration

The llama.cpp server runs with:
- **6 parallel slots** for concurrent inference
- **Vulkan GPU** acceleration
- **16K context** window

## 🧪 Usage

```bash
# Single agent
python run_test.py "list files in sandbox/"

# Parallel agents (3 workers, vote on best)
python run_test.py "create hello.py" --poetiq

# Parallel with 6 workers
python run_test.py "task" --poetiq -p 6

# Stress test
python run_test.py --stress 6
```

## 📊 Performance

| Mode | Time | 
|------|------|
| LM Studio (old) | ~5 min |
| **Poetiq + llama.cpp** | **~10s** |

## 🛠️ Requirements

```
openai
requests
```

## 📜 Based on

- [Self-Refine Paper](https://arxiv.org/abs/2303.17651)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
