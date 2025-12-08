# Guía del Modelo Local (Liquid LMF2)

Este documento explica cómo está configurado el modelo LLM local y las decisiones de diseño.

---

## 📋 Por Qué Usamos LLM Local (No APIs de Pago)

### Razones Principales:

| Razón | Explicación |
|-------|-------------|
| **Costo** | APIs como OpenAI/Anthropic cobran por token. Para iteración continua (cientos de llamadas/día), el costo es prohibitivo |
| **Privacidad** | Todo se ejecuta localmente. No hay datos enviados a servidores externos |
| **Velocidad de Iteración** | Podemos hacer 10+ llamadas por minuto sin límites de rate |
| **Hardware Disponible** | Este sistema está diseñado para GPUs de consumidor (AMD/NVIDIA) vía llama.cpp |
| **Aprendizaje Continuo** | El modelo puede fallar y aprender sin costo económico |

### Trade-offs Aceptados:

- ❌ Modelo más pequeño = Menos "inteligente" que GPT-4/Claude
- ✅ PERO: Iteración rápida + Self-Refine compensa la diferencia
- ✅ PERO: Podemos hacer 100 intentos donde otros harían 1

---

## 🔧 Modelo Actual: Liquid LMF2

### Especificaciones:
- **Tamaño**: ~2.6B-3B parámetros (pequeño)
- **Ventaja**: Muy rápido en hardware limitado
- **Debilidad**: No fue diseñado para tool-use nativo
- **Contexto**: Soporta hasta 32k tokens

### Limitaciones Conocidas:
1. **Alucina nombres de tools** - Inventa tools que no existen
2. **Razonamiento complejo limitado** - No maneja muchas instrucciones simultáneas
3. **Sensible a temperatura** - Temps altas (>0.5) causan más errores

---

## 🌡️ Configuración de Temperatura

### ¿Qué es la Temperatura?
La temperatura controla qué tan "creativo" vs "determinístico" es el modelo:

| Temperatura | Efecto | Uso |
|-------------|--------|-----|
| 0.0-0.2 | Muy determinístico, repite patrones | Evaluación, verificación |
| 0.2-0.4 | Balanceado, menos errores | **Nuestro rango óptimo** |
| 0.5-0.7 | Más creativo, más variación | Generación de ideas |
| 0.8-1.0+ | Muy aleatorio, más alucinaciones | Evitar para tareas precisas |

### Configuración Actual (Optimizada para LMF2):
```python
# config/settings.py
TEMPERATURE = 0.3           # Default bajo para estabilidad
WORKER_TEMPS = [0.2, 0.3, 0.4]  # Variación mínima en paralelo
```

### Evidencia Científica (2024):
- Research de ArXiv muestra que temperaturas altas aumentan probabilidad de alucinación
- Para modelos pequeños (7B o menos), se recomienda temp ≤ 0.3
- Temp=0 no es ideal porque puede atascarse en patrones repetitivos

---

## 💬 Cómo Hacer Prompts para LMF2

### Best Practices (De la documentación oficial de Liquid AI):

1. **Usar tokens `<think></think>` para Chain-of-Thought**:
   ```
   <think>
   - ¿Qué pide la tarea?
   - ¿Qué herramienta necesito?
   - ¿Qué parámetros?
   </think>
   
   {respuesta}
   ```

2. **Ser PRECISO y CONCISO**:
   - ❌ "Podrías tal vez considerar usar alguna herramienta para leer archivos..."
   - ✅ "Usa `read_file` con el parámetro `path`."

3. **Una instrucción a la vez**:
   - ❌ "Lee el archivo, analízalo, extrae X, guárdalo en Y, y haz un test"
   - ✅ "Lee el archivo X" → (siguiente turno) → "Analiza el contenido"

4. **Formato de salida explícito**:
   ```
   Responde en JSON:
   {"tool": "...", "params": {...}}
   ```

5. **Evitar instrucciones negativas complejas**:
   - ❌ "No uses herramientas que no estén en la lista ni inventes parámetros"
   - ✅ "Usa SOLO estas herramientas: read_file, write_file, list_dir"

---

## 🔄 Cómo Maneja el Sistema las Limitaciones

| Limitación | Solución Implementada |
|------------|----------------------|
| Alucina tools | `execute_tool()` sugiere tools existentes cuando falla |
| Pierde el mejor código | `SelfRefiner` guarda el mejor score, no el último |
| Connection errors | Retry con backoff exponencial (1s, 2s, 4s) |
| Servidor se cuelga | Health check + auto-restart |
| Olvida contexto | Memory Orchestrator inyecta memorias relevantes |

---

## 📊 Parámetros Recomendados por Liquid AI

```python
# Recomendación oficial de LMF2
temperature = 0.3
min_p = 0.15
repetition_penalty = 1.05
```

Nuestro sistema usa estos valores (excepto `min_p` que depende del servidor llama.cpp).

---

## 🎯 Resumen

1. **Usamos LLM local** porque es gratis, privado, y permite iteración rápida
2. **LMF2 es pequeño pero suficiente** con las técnicas de Self-Refine
3. **Temperaturas bajas (0.2-0.4)** reducen alucinaciones
4. **Tokens `<think></think>`** mejoran el razonamiento del modelo
5. **El sistema compensa las limitaciones** con memoria, retry, y best-code tracking
