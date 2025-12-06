# Parallel Module - Multi-threading for candidate generation and evaluation

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
import time


class ParallelExecutor:
    """Execute multiple LLM calls in parallel"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
    
    def generate_candidates(
        self,
        generator_fn: Callable[[], str],
        num_candidates: int = 3
    ) -> List[str]:
        """
        Generate multiple response candidates in parallel
        
        Args:
            generator_fn: Function that generates a response
            num_candidates: Number of candidates to generate
            
        Returns:
            List of response strings
        """
        candidates = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(generator_fn) for _ in range(num_candidates)]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    if result:
                        candidates.append(result)
                except Exception as e:
                    print(f"  ⚠️ Candidate generation failed: {e}")
        
        return candidates
    
    def evaluate_parallel(
        self,
        evaluator_fn: Callable[[str], Dict[str, Any]],
        candidates: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple candidates in parallel
        
        Args:
            evaluator_fn: Function that evaluates a response
            candidates: List of responses to evaluate
            
        Returns:
            List of evaluation results with scores
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_candidate = {
                executor.submit(evaluator_fn, c): c 
                for c in candidates
            }
            
            for future in as_completed(future_to_candidate):
                candidate = future_to_candidate[future]
                try:
                    eval_result = future.result(timeout=60)
                    eval_result["response"] = candidate
                    results.append(eval_result)
                except Exception as e:
                    print(f"  ⚠️ Evaluation failed: {e}")
        
        return results
    
    def select_best(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best response based on evaluation scores"""
        if not evaluations:
            return {"response": "", "score": 0, "feedback": "No evaluations"}
        
        return max(evaluations, key=lambda x: x.get("score", 0))


class CandidateGenerator:
    """Generate multiple response candidates with different strategies"""
    
    def __init__(self, llm, parallel_executor: ParallelExecutor = None):
        self.llm = llm
        self.executor = parallel_executor or ParallelExecutor()
    
    def generate_with_voting(
        self,
        messages: List[Dict],
        evaluator_fn: Callable,
        num_candidates: int = 3
    ) -> Dict[str, Any]:
        """
        Generate multiple candidates, evaluate them, and return the best
        
        Args:
            messages: Chat messages for LLM
            evaluator_fn: Function to evaluate responses
            num_candidates: Number of candidates to generate
            
        Returns:
            Best response with evaluation
        """
        print(f"  🔀 Generating {num_candidates} candidates...")
        
        # Generate candidates with different temperatures
        candidates = []
        temps = [0.5, 0.7, 0.9][:num_candidates]
        
        for i, temp in enumerate(temps):
            try:
                response = self.llm.chat(messages, temp=temp)
                if response:
                    candidates.append(response)
                    print(f"    ✓ Candidate {i+1} (temp={temp})")
            except Exception as e:
                print(f"    ✗ Candidate {i+1} failed: {e}")
        
        if not candidates:
            return {"response": "", "score": 0}
        
        # Evaluate all candidates
        print(f"  📊 Evaluating {len(candidates)} candidates...")
        evaluations = self.executor.evaluate_parallel(evaluator_fn, candidates)
        
        # Select best
        best = self.executor.select_best(evaluations)
        print(f"  ✨ Best score: {best.get('score', 0)}/25")
        
        return best
