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

## 📜 Architecture & Sources

This project implements the **Poetiq Architecture** for autonomous AI reasoning:

### Core Papers & Research
- [Self-Refine Paper](https://arxiv.org/abs/2303.17651) - Iterative Refinement with Self-Feedback (Madaan et al., 2023)
- [Ryan Greenblatt's ARC-AGI Approach](https://github.com/rgreenblatt/arc_prism) - Getting 50% on ARC-AGI with GPT-4o (Program Synthesis)

### Poetiq Architecture (2025)
- [Poetiq GitHub Repo](https://github.com/poetiq-ai/poetiq-arc-agi-solver) - Official code
- [Poetiq Blog: Traversing the Frontier](https://poetiq.ai/posts/arcagi_announcement/) - Full technical breakdown
- [Poetiq Blog: Shatters ARC-AGI-2](https://poetiq.ai/posts/arcagi_verified/) - Verified results

### Key Concepts
| Concept | Description |
|---------|-------------|
| **Program Synthesis** | LLM generates Python code, not just text answers |
| **Test-Time Compute** | More inference time → better results (log-linear) |
| **Verification Loop** | Execute code against examples, if fail → feedback → retry |
| **Self-Auditing** | System decides when solution is satisfactory |
| **Pareto-Optimal Routing** | Use cheap models for easy tasks, expensive for hard |

### ARC-AGI Benchmark
- [ARC Prize Official](https://arcprize.org/) - The benchmark that Poetiq conquered
- [ARC-AGI-2 Leaderboard](https://arcprize.org/leaderboard)

### llama.cpp
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Our local inference server

