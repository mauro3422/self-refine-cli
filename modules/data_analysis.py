# Análisis CSV con pandas - Self-Refine Architecture

import os
from typing import Dict, Optional
from core.llm_client import LLMClient
from core.refiner import SelfRefiner
from core.executor import CodeExecutor
from prompts.templates import (
    DATA_ANALYSIS_PROMPT,
    DATA_EVALUATION_PROMPT,
    DATA_REFINEMENT_PROMPT
)


class DataAnalyzer:
    def __init__(self):
        self.llm = LLMClient()
        self.refiner = SelfRefiner()
        self.executor = CodeExecutor()
    
    def generate_analysis_code(self, file_path: str, task: str) -> str:
        """Genera código de análisis para CSV"""
        prompt = DATA_ANALYSIS_PROMPT.format(
            file_path=file_path,
            task=task
        )
        return self._clean_code(self.llm.generate(prompt))
    
    def evaluate(self, task: str, output: str, exec_result: Optional[Dict] = None) -> str:
        """Evalúa análisis de datos con feedback multi-dimensional"""
        # Parsear task para extraer file_path
        file_path = task.split("CSV:")[1].strip() if "CSV:" in task else "unknown"
        task_desc = task.split("CSV:")[0].strip() if "CSV:" in task else task
        
        exec_str = self.executor.format_result(exec_result) if exec_result else "No ejecutado"
        
        prompt = DATA_EVALUATION_PROMPT.format(
            task=task_desc,
            file_path=file_path,
            output=output,
            exec_result=exec_str
        )
        return self.llm.generate(prompt, temp=0.3)
    
    def refine(self, task: str, output: str, feedback: str, 
               exec_result: Optional[Dict] = None, history: str = "") -> str:
        """Refina código de análisis con historial"""
        file_path = task.split("CSV:")[1].strip() if "CSV:" in task else "unknown"
        task_desc = task.split("CSV:")[0].strip() if "CSV:" in task else task
        
        prompt = DATA_REFINEMENT_PROMPT.format(
            file_path=file_path,
            task=task_desc,
            output=output,
            feedback=feedback,
            history=history if history else "Ninguno"
        )
        return self._clean_code(self.llm.generate(prompt))
    
    def _clean_code(self, code: str) -> str:
        """Limpia markdown del código"""
        code = code.strip()
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0] if len(parts) > 2 else parts[1]
        return code.strip()
    
    def analyze_csv(self, file_path: str, task: str = "análisis general") -> Dict:
        """Analiza CSV con self-refinement"""
        if not os.path.exists(file_path):
            return {"error": f"Archivo no encontrado: {file_path}"}
        
        print(f"\n{'='*60}")
        print(f"📊 Analizando CSV: {file_path}")
        print(f"📋 Tarea: {task}")
        print(f"{'='*60}")
        
        # Combinar file_path y task para el refiner
        combined_task = f"{task} CSV: {file_path}"
        
        initial_code = self.generate_analysis_code(file_path, task)
        print(f"\n✅ Código de análisis generado ({len(initial_code)} chars)")
        
        result = self.refiner.refine_loop(
            initial_output=initial_code,
            task=combined_task,
            evaluate_fn=self.evaluate,
            refine_fn=self.refine,
            execute_code=True,
            history_context=True
        )
        
        result["improvement_summary"] = self.refiner.get_improvement_summary()
        print(f"\n📈 {result['improvement_summary']}")
        
        return result
