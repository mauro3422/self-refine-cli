# Memory Module - Full A-mem with Orchestrator
# Single unified interface for all memory operations

from memory.base import SmartMemory, AgentMemory, get_memory
from memory.learner import MemoryLearner
from memory.vector_store import VectorMemory, get_vector_memory
from memory.evolution import MemoryEvolution, get_evolution
from memory.context_vectors import (
    ContextVectors, InContextVector, 
    get_context_vectors, get_icv, build_smart_context
)
from memory.graph import MemoryGraph, get_memory_graph
from memory.llm_linker import LLMLinker, get_llm_linker
from memory.orchestrator import MemoryOrchestrator, get_orchestrator, get_memory_context

__all__ = [
    # Core
    'SmartMemory', 'AgentMemory', 'get_memory',
    # Orchestrator (main interface)
    'MemoryOrchestrator', 'get_orchestrator', 'get_memory_context',
    # Components
    'MemoryLearner',
    'VectorMemory', 'get_vector_memory',
    'MemoryGraph', 'get_memory_graph',
    'LLMLinker', 'get_llm_linker',
    'ContextVectors', 'InContextVector', 
    'get_context_vectors', 'get_icv', 'build_smart_context',
    'MemoryEvolution', 'get_evolution',
]

