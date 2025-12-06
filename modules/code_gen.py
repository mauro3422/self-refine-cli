# Generación de código - Self-Refine Architecture

from typing import Dict, Optional
from core.llm_client import LLMClient
from core.refiner import SelfRefiner
from core.executor import CodeExecutor
from prompts.templates import (
    CODE_GENERATION_PROMPT, 
    CODE_EVALUATION_PROMPT,
    CODE_REFINEMENT_PROMPT
)


class CodeGenerator:
    def __init__(self):
        self.llm = LLMClient()
        self.refiner = SelfRefiner()
        self.executor = CodeExecutor()
    
    def generate(self, task: str) -> str:
        """Genera código inicial"""
        prompt = CODE_GENERATION_PROMPT.format(task=task)
        return self.llm.generate(prompt)
    
    def evaluate(self, task: str, output: str, exec_result: Optional[Dict] = None) -> str:
        """
        Evalúa código generado con feedback multi-dimensional.
        Retorna feedback con scores 1-5 por dimensión.
        """
        exec_str = self.executor.format_result(exec_result) if exec_result else "No ejecutado"
        
        prompt = CODE_EVALUATION_PROMPT.format(
            task=task,
            output=output,
            exec_result=exec_str
        )
        return self.llm.generate(prompt, temp=0.3)  # Lower temp for consistent evaluation
    
    def refine(self, task: str, output: str, feedback: str, 
               exec_result: Optional[Dict] = None, history: str = "") -> str:
        """
        Refina código según feedback.
        Incluye historial para evitar repetir errores.
        """
        exec_str = ""
        if exec_result:
            exec_str = exec_result.get("error", "") or exec_result.get("output", "")
        
        prompt = CODE_REFINEMENT_PROMPT.format(
            task=task,
            output=output,
            feedback=feedback,
            exec_result=exec_str,
            history=history if history else "Ninguno"
        )
        
        # Limpiar markdown del output si el modelo lo incluye
        result = self.llm.generate(prompt)
        return self._clean_code(result)
    
    def _clean_code(self, code: str) -> str:
        """Limpia markdown y texto extra del código"""
        code = code.strip()
        
        # Remover bloques de código markdown
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) > 1:
                code = parts[1].split("```")[0] if len(parts) > 2 else parts[1]
        
        return code.strip()
    
    def generate_with_refinement(self, task: str) -> Dict:
        """
        Genera código con self-refinement completo.
        Ejecuta código y usa resultado como feedback adicional.
        """
        print(f"\n{'='*60}")
        print(f"📝 Generando código para: {task}")
        print(f"{'='*60}")
        
        # Generar código inicial
        initial_code = self.generate(task)
        initial_code = self._clean_code(initial_code)
        print(f"\n✅ Código inicial generado ({len(initial_code)} chars)")
        
        # Self-refine loop
        result = self.refiner.refine_loop(
            initial_output=initial_code,
            task=task,
            evaluate_fn=self.evaluate,
            refine_fn=self.refine,
            execute_code=True,
            history_context=True
        )
        
        # Agregar resumen de mejora
        result["improvement_summary"] = self.refiner.get_improvement_summary()
        print(f"\n📈 {result['improvement_summary']}")
        
        return result
