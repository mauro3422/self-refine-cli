# Debugging de código - Self-Refine Architecture

from typing import Dict, Optional
from core.llm_client import LLMClient
from core.refiner import SelfRefiner
from core.executor import CodeExecutor
from prompts.templates import (
    DEBUG_PROMPT,
    DEBUG_EVALUATION_PROMPT,
    DEBUG_REFINEMENT_PROMPT
)


class CodeDebugger:
    def __init__(self):
        self.llm = LLMClient()
        self.refiner = SelfRefiner()
        self.executor = CodeExecutor()
        self._original_code = ""  # Store for evaluation
    
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
    
    def _extract_code_from_debug(self, response: str) -> str:
        """Extrae código corregido de respuesta de debug"""
        response_lower = response.lower()
        
        # Buscar después de "código corregido"
        markers = ["código corregido", "corrected code", "fixed code"]
        for marker in markers:
            if marker in response_lower:
                idx = response_lower.find(marker)
                code_part = response[idx:]
                
                # Tomar desde el marcador hasta el final o siguiente sección
                if "explicación" in code_part.lower():
                    code_part = code_part[:code_part.lower().find("explicación")]
                
                return self._clean_code(code_part)
        
        # Si no encuentra marcador, intentar limpiar todo
        return self._clean_code(response)
    
    def debug(self, buggy_code: str) -> Dict:
        """Debuggea código con errores usando self-refinement"""
        self._original_code = buggy_code
        
        print(f"\n{'='*60}")
        print(f"🐛 Debuggeando código...")
        print(f"{'='*60}")
        
        # Ejecutar código buggy para obtener error
        exec_result = self.executor.execute(buggy_code)
        
        if exec_result["status"] == "success":
            return {
                "message": "El código no tiene errores de ejecución",
                "output": exec_result["output"],
                "total_iterations": 0
            }
        
        error = exec_result["error"]
        print(f"\n❌ Error encontrado:")
        print(f"   {error[:200]}...")
        
        # Generar corrección inicial
        prompt = DEBUG_PROMPT.format(code=buggy_code, error=error)
        initial_fix_raw = self.llm.generate(prompt)
        initial_fix = self._extract_code_from_debug(initial_fix_raw)
        
        print(f"\n🔧 Corrección inicial generada ({len(initial_fix)} chars)")
        
        # Self-refine loop
        result = self.refiner.refine_loop(
            initial_output=initial_fix,
            task=buggy_code,  # Original code as "task"
            evaluate_fn=self._evaluate_debug,
            refine_fn=self._refine_debug,
            execute_code=True,
            history_context=True
        )
        
        result["original_error"] = error
        result["improvement_summary"] = self.refiner.get_improvement_summary()
        print(f"\n📈 {result['improvement_summary']}")
        
        return result
    
    def _evaluate_debug(self, task: str, output: str, exec_result: Optional[Dict] = None) -> str:
        """Evalúa corrección de bug"""
        exec_str = self.executor.format_result(exec_result) if exec_result else "No ejecutado"
        
        prompt = DEBUG_EVALUATION_PROMPT.format(
            original_code=self._original_code,
            output=output,
            exec_result=exec_str
        )
        return self.llm.generate(prompt, temp=0.3)
    
    def _refine_debug(self, task: str, output: str, feedback: str,
                      exec_result: Optional[Dict] = None, history: str = "") -> str:
        """Refina corrección de bug"""
        prompt = DEBUG_REFINEMENT_PROMPT.format(
            original_code=self._original_code,
            output=output,
            feedback=feedback,
            history=history if history else "Ninguno"
        )
        return self._clean_code(self.llm.generate(prompt))
