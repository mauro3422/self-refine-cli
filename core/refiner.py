# Loop de self-refinement - Self-Refine Architecture
# Based on: https://arxiv.org/abs/2303.17651

import re
from typing import Dict, Callable, Optional, List, Any
from core.llm_client import LLMClient
from core.executor import CodeExecutor
from config.settings import MAX_ITERATIONS, SCORE_THRESHOLD


class SelfRefiner:
    def __init__(self):
        self.llm = LLMClient()
        self.executor = CodeExecutor()
        self.iterations_history: List[Dict] = []
    
    def _extract_score(self, feedback: str) -> int:
        """
        Extrae el score total del feedback.
        Busca patrones como "TOTAL: 21/25" o "Total score: 21/25"
        """
        patterns = [
            r'TOTAL[:\s]+(\d+)/25',
            r'Total[:\s]+(\d+)/25',
            r'total[:\s]+(\d+)/25',
            r'(\d+)/25',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, feedback)
            if match:
                return int(match.group(1))
        
        return 0  # Default if no score found
    
    def _is_sufficient(self, feedback: str, score: int) -> bool:
        """
        Determina si el output es suficientemente bueno.
        Criterios (más estrictos para evitar paradas prematuras):
        1. Score >= SCORE_THRESHOLD (23/25) → para incondicionalmente
        2. Score >= 20 Y modelo dice NO_IMPROVEMENTS_NEEDED → para
        3. Score < 20 → siempre continúa refinando
        """
        # Si alcanza el threshold, parar
        if score >= SCORE_THRESHOLD:
            return True
        
        # Si el modelo dice que está bien pero el score es bajo, continuar
        if "NO_IMPROVEMENTS_NEEDED" in feedback.upper():
            # Solo confiar en el modelo si el score es razonablemente alto
            if score >= 20:
                return True
            else:
                print(f"  ⚠️ Modelo dijo NO_IMPROVEMENTS pero score={score}<20, continuando...")
                return False
        
        return False
    
    def _format_history(self, history: List[Dict], max_entries: int = 2) -> str:
        """
        Formatea historial de iteraciones previas para incluir en prompt.
        Solo últimas N entradas para no saturar contexto.
        """
        if not history:
            return "Ninguno"
        
        recent = history[-max_entries:]
        formatted = []
        
        for h in recent:
            entry = f"Iteración {h['iteration']}:\n"
            entry += f"  Score: {h.get('score', 'N/A')}/25\n"
            
            # Incluir solo resumen del feedback, no todo
            fb = h.get('feedback', '')
            if fb:
                # Extraer primera línea o problema principal
                lines = fb.strip().split('\n')
                summary = lines[0][:100] if lines else "Sin feedback"
                entry += f"  Problema: {summary}...\n"
            
            formatted.append(entry)
        
        return "\n".join(formatted)
    
    def refine_loop(self, initial_output: str, task: str, 
                    evaluate_fn: Callable, refine_fn: Callable, 
                    execute_code: bool = False,
                    history_context: bool = True) -> Dict:
        """
        Loop genérico de self-refinement siguiendo el paper.
        
        Args:
            initial_output: Output inicial a refinar
            task: Descripción de la tarea
            evaluate_fn: Función que evalúa y retorna feedback (task, output, exec_result) -> str
            refine_fn: Función que refina (task, output, feedback, exec_result, history) -> str
            execute_code: Si True, ejecuta código y usa resultado como feedback
            history_context: Si True, incluye historial en prompts de refinamiento
        
        Returns:
            {final_output, iterations, total_iterations, final_score}
        """
        output = initial_output
        self.iterations_history = []
        
        for i in range(1, MAX_ITERATIONS + 1):
            print(f"\n🔄 Iteración {i}/{MAX_ITERATIONS}")
            
            # Paso 1: Ejecutar código si es necesario
            exec_result = None
            if execute_code:
                exec_result = self.executor.execute(output)
                status_icon = "✓" if exec_result["status"] == "success" else "✗"
                print(f"  ▶️  Ejecución: {status_icon} {exec_result['status']}")
                
                # Mostrar output truncado si hay
                if exec_result.get("output"):
                    out_preview = exec_result["output"][:100].replace('\n', ' ')
                    print(f"     Output: {out_preview}...")
            
            # Paso 2: Generar FEEDBACK
            print(f"  📝 Evaluando...")
            feedback = evaluate_fn(task, output, exec_result)
            
            # Extraer score del feedback
            score = self._extract_score(feedback)
            print(f"  📊 Score: {score}/25")
            
            # Guardar iteración
            iteration_data = {
                "iteration": i,
                "output": output,
                "output_length": len(output),
                "feedback": feedback,
                "score": score,
                "execution": exec_result
            }
            self.iterations_history.append(iteration_data)
            
            # Paso 3: Verificar stopping criteria
            if self._is_sufficient(feedback, score):
                print(f"  ✨ Óptimo alcanzado en iteración {i} (score: {score}/25)")
                break
            
            # Paso 4: REFINE si no es la última iteración
            if i < MAX_ITERATIONS:
                print(f"  🔧 Refinando...")
                
                # Preparar historial si está habilitado
                history_str = ""
                if history_context:
                    history_str = self._format_history(self.iterations_history)
                
                output = refine_fn(task, output, feedback, exec_result, history_str)
            else:
                print(f"  ⚠️ Máximo de iteraciones alcanzado")
        
        # Resultado final
        final_score = self.iterations_history[-1]["score"] if self.iterations_history else 0
        
        return {
            "final_output": output,
            "iterations": self.iterations_history,
            "total_iterations": len(self.iterations_history),
            "final_score": final_score,
            "reached_threshold": final_score >= SCORE_THRESHOLD
        }
    
    def get_improvement_summary(self) -> str:
        """Genera resumen de mejora a través de iteraciones"""
        if len(self.iterations_history) < 2:
            return "No hubo refinamiento"
        
        first_score = self.iterations_history[0].get("score", 0)
        last_score = self.iterations_history[-1].get("score", 0)
        improvement = last_score - first_score
        
        return f"Score: {first_score} → {last_score} (Δ{'+' if improvement >= 0 else ''}{improvement})"
