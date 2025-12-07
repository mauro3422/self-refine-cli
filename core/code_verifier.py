# Code Verifier - Poetiq-style program synthesis verification
# Executes generated code against test cases and provides feedback

import traceback
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from core.executor import CodeExecutor


@dataclass
class VerifyResult:
    """Result of code verification against test cases"""
    passed: bool
    total_tests: int
    passed_tests: int
    failures: List[Dict]  # [{input, expected, actual, error}]
    execution_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    def to_feedback(self) -> str:
        """Convert result to feedback string for refinement"""
        if self.execution_error:
            return f"CODE ERROR: {self.execution_error}"
        
        if self.passed:
            return f"CODE PASSED: All {self.total_tests} test cases passed."
        
        # Build failure feedback
        lines = [f"CODE FAILED: {self.passed_tests}/{self.total_tests} tests passed."]
        for i, fail in enumerate(self.failures[:3]):  # Max 3 failures shown
            lines.append(f"  Test {i+1}: Expected '{fail['expected']}', got '{fail['actual']}'")
            if fail.get('error'):
                lines.append(f"    Error: {fail['error']}")
        
        return "\n".join(lines)


class CodeVerifier:
    """
    Poetiq-style code verification with FULL Memory Orchestrator integration.
    Executes generated Python code against test cases.
    Learns from verification results using the complete memory pipeline:
    - LLMLinker for intelligent memory retrieval
    - Graph linking for related memories
    - Feedback marking for reinforcement learning
    """
    
    def __init__(self, orchestrator=None):
        self.executor = CodeExecutor()
        
        # Connect to FULL memory orchestrator (not just SmartMemory)
        if orchestrator is None:
            from memory.orchestrator import get_orchestrator
            self.orchestrator = get_orchestrator()
        else:
            self.orchestrator = orchestrator
        
        # Track verification history for this session
        self.verification_history = []
    
    def _learn_from_result(self, code: str, result: 'VerifyResult', task_hint: str = ""):
        """
        Learn from verification result and store in memory.
        Called automatically after each verification.
        """
        if not self.orchestrator:
            return
        
        # Track in session history
        self.verification_history.append({
            'passed': result.passed,
            'error': result.execution_error,
            'success_rate': result.success_rate
        })
        
        # Only learn from failures (more valuable lessons)
        if result.passed:
            # Small positive reinforcement for passing patterns
            if task_hint:
                lesson = f"PATTERN: For '{task_hint[:50]}', the solve() approach works well."
                self.orchestrator.learn(
                    lesson=lesson,
                    category="code_pattern",
                    tools=["python_exec"]
                )
            return
        
        # Learn from failures
        if result.execution_error:
            # Syntax/structure errors
            error_type = "syntax" if "Syntax" in result.execution_error else "structure"
            lesson = f"AVOID: {result.execution_error}"
            self.orchestrator.learn(
                lesson=lesson,
                category="code_error",
                tools=["python_exec"],
                error_type=error_type
            )
        elif result.failures:
            # Logic errors - learn from the pattern
            fail = result.failures[0]
            lesson = f"LOGIC_ERROR: Input '{fail['input']}' expected '{fail['expected']}' but got '{fail['actual']}'. Check edge cases."
            self.orchestrator.learn(
                lesson=lesson,
                category="code_logic",
                tools=["python_exec"],
                error_type="logic_failure"
            )
    
    def get_memory_hints(self, task_description: str) -> str:
        """Get relevant memories for code generation hints using Orchestrator"""
        if not self.orchestrator:
            return ""
        
        # Use Orchestrator's full context retrieval (includes LLM linking)
        context = self.orchestrator.get_context(
            query=f"python code: {task_description}", 
            use_llm=True
        )
        
        if not context.memories:
            return ""
        
        # Filter for code-related memories
        code_memories = [m for m in context.memories 
                        if m.get('category', '').startswith('code')]
        
        if not code_memories:
            # Fall back to all memories if no code-specific ones
            code_memories = context.memories[:3]
        
        hints = ["MEMORY HINTS FOR CODE GENERATION:"]
        for mem in code_memories[:3]:
            hints.append(f"  - {mem.get('lesson', '')[:100]}")
        
        if context.tips:
            hints.append(f"\nTIPS: {context.tips}")
        
        return "\n".join(hints)
    
    def verify(self, code: str, test_cases: List[Dict]) -> VerifyResult:
        """
        Execute code against each test case.
        
        Args:
            code: Python code to test (should define a 'solve' function)
            test_cases: List of {input: ..., expected: ...}
        
        Returns:
            VerifyResult with pass/fail status and details
        """
        if not test_cases:
            return VerifyResult(
                passed=True, 
                total_tests=0, 
                passed_tests=0, 
                failures=[]
            )
        
        # First, try to execute the code to check for syntax errors
        try:
            # Create isolated namespace for the code
            namespace = {}
            exec(code, namespace)
            
            # Check if 'solve' function exists
            if 'solve' not in namespace:
                return VerifyResult(
                    passed=False,
                    total_tests=len(test_cases),
                    passed_tests=0,
                    failures=[],
                    execution_error="Code must define a 'solve(input)' function"
                )
            
            solve_func = namespace['solve']
            
        except Exception as e:
            return VerifyResult(
                passed=False,
                total_tests=len(test_cases),
                passed_tests=0,
                failures=[],
                execution_error=f"Syntax error: {str(e)}"
            )
        
        # Run each test case
        passed_count = 0
        failures = []
        
        for test in test_cases:
            test_input = test.get('input')
            expected = test.get('expected')
            
            try:
                actual = solve_func(test_input)
                
                if actual == expected:
                    passed_count += 1
                else:
                    failures.append({
                        'input': test_input,
                        'expected': expected,
                        'actual': actual,
                        'error': None
                    })
                    
            except Exception as e:
                failures.append({
                    'input': test_input,
                    'expected': expected,
                    'actual': None,
                    'error': str(e)
                })
        
        return VerifyResult(
            passed=(passed_count == len(test_cases)),
            total_tests=len(test_cases),
            passed_tests=passed_count,
            failures=failures
        )
    
    def verify_and_learn(self, code: str, test_cases: List[Dict], task_hint: str = "") -> VerifyResult:
        """
        Verify code and automatically learn from the result.
        This is the recommended method for production use.
        """
        result = self.verify(code, test_cases)
        self._learn_from_result(code, result, task_hint)
        return result
    
    def verify_with_retry_feedback(self, code: str, test_cases: List[Dict], 
                                    previous_attempts: List[str] = None) -> Dict:
        """
        Verify code and generate structured feedback for retry.
        
        Returns dict with:
            - result: VerifyResult
            - feedback: str for LLM
            - should_retry: bool
        """
        result = self.verify(code, test_cases)
        
        feedback_parts = [result.to_feedback()]
        
        # Add context about previous attempts if any
        if previous_attempts:
            feedback_parts.append(f"\nPrevious attempts: {len(previous_attempts)}")
            if len(previous_attempts) >= 3:
                feedback_parts.append("Consider a different approach entirely.")
        
        return {
            'result': result,
            'feedback': "\n".join(feedback_parts),
            'should_retry': not result.passed and len(previous_attempts or []) < 5
        }


# Test case format for Poetiq-style tasks
@dataclass
class PoetiqTask:
    """A task with test cases for verification"""
    description: str
    test_cases: List[Dict]  # [{input: ..., expected: ...}]
    
    @classmethod
    def from_examples(cls, description: str, examples: List[tuple]):
        """Create from list of (input, expected) tuples"""
        test_cases = [
            {'input': inp, 'expected': exp} 
            for inp, exp in examples
        ]
        return cls(description=description, test_cases=test_cases)


# Singleton
_verifier: Optional[CodeVerifier] = None

def get_verifier() -> CodeVerifier:
    global _verifier
    if _verifier is None:
        _verifier = CodeVerifier()
    return _verifier
