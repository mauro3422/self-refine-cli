# core/poetiq.py
# WRAPPER FILE - Maintains backward compatibility
# The actual implementation is now in core/poetiq/ folder (modularized)

"""
True Poetiq System - Now Modularized!

The system has been split into smaller modules for easier maintenance:
- core/poetiq/worker.py      - LightWorker, WorkerResponse
- core/poetiq/executor.py    - ToolExecutor
- core/poetiq/aggregator.py  - Aggregator
- core/poetiq/refiner.py     - SelfRefiner
- core/poetiq/runner.py      - PoetiqRunner, run_poetiq

This file re-exports everything for backward compatibility.
"""

# Re-export all components from the modularized package
from core.poetiq import (
    # Data classes
    WorkerResponse,
    
    # Core classes
    LightWorker,
    ToolExecutor,
    Aggregator,
    SelfRefiner,
    PoetiqRunner,
    
    # Convenience function
    run_poetiq,
)

__all__ = [
    'WorkerResponse',
    'LightWorker',
    'ToolExecutor',
    'Aggregator',
    'SelfRefiner',
    'PoetiqRunner',
    'run_poetiq',
]
