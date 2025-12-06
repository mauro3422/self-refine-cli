# Prompts para cada tipo de tarea - Self-Refine Architecture
# Based on: https://arxiv.org/abs/2303.17651

# =============================================================================
# CODE GENERATION PROMPTS
# =============================================================================

CODE_GENERATION_PROMPT = """Genera código Python para: {task}

Requisitos:
- SOLO código, sin explicaciones ni markdown
- Código completo y ejecutable
- Incluye imports necesarios
- Usa nombres descriptivos
- Incluye manejo de errores básico

Código:"""

CODE_EVALUATION_PROMPT = """Evalúa este código en múltiples dimensiones:

TAREA: {task}

CÓDIGO:
```python
{output}
```

RESULTADO DE EJECUCIÓN:
{exec_result}

Evalúa cada dimensión (1-5 puntos):

1. **Corrección** (¿Funciona correctamente?)
   - Score: X/5
   - Problema específico: [ubicación exacta si hay error]
   - Mejora: [instrucción concreta]

2. **Eficiencia** (¿Es óptimo?)
   - Score: X/5
   - Problema específico: [línea o sección ineficiente]
   - Mejora: [instrucción concreta]

3. **Legibilidad** (¿Es claro?)
   - Score: X/5
   - Problema específico: [código confuso]
   - Mejora: [instrucción concreta]

4. **Casos Edge** (¿Maneja todos los casos?)
   - Score: X/5
   - Problema específico: [caso no manejado]
   - Mejora: [instrucción concreta]

5. **Buenas Prácticas** (¿Sigue estándares?)
   - Score: X/5
   - Problema específico: [violación de práctica]
   - Mejora: [instrucción concreta]

TOTAL: XX/25

Si TOTAL >= 23/25, responde EXACTAMENTE: "NO_IMPROVEMENTS_NEEDED"
Si no, proporciona el feedback detallado arriba."""

CODE_REFINEMENT_PROMPT = """Mejora este código según el feedback:

TAREA ORIGINAL: {task}

CÓDIGO ACTUAL:
```python
{output}
```

RESULTADO DE EJECUCIÓN:
{exec_result}

FEEDBACK:
{feedback}

HISTORIAL DE INTENTOS PREVIOS (para NO repetir errores):
{history}

Genera el código mejorado aplicando TODAS las mejoras sugeridas.
SOLO código Python, sin explicaciones ni markdown:"""

# =============================================================================
# DATA ANALYSIS PROMPTS
# =============================================================================

DATA_ANALYSIS_PROMPT = """Genera código Python con pandas para analizar este CSV:

ARCHIVO: {file_path}
TAREA: {task}

El código debe:
- Cargar el CSV con pandas
- Realizar análisis descriptivo
- Generar insights relevantes
- Imprimir resultados claros con formato

SOLO código ejecutable:"""

DATA_EVALUATION_PROMPT = """Evalúa este código de análisis de datos:

TAREA: {task}
ARCHIVO CSV: {file_path}

CÓDIGO:
```python
{output}
```

RESULTADO:
{exec_result}

Evalúa cada dimensión (1-5 puntos):

1. **Carga Correcta** (¿Se cargó el CSV bien?)
   - Score: X/5
   - Problema: [si hay error de carga]
   - Mejora: [instrucción]

2. **Análisis Completo** (¿Responde la tarea?)
   - Score: X/5
   - Problema: [análisis faltante]
   - Mejora: [instrucción]

3. **Insights** (¿Genera conclusiones útiles?)
   - Score: X/5
   - Problema: [insight faltante]
   - Mejora: [instrucción]

4. **Presentación** (¿Los prints son claros?)
   - Score: X/5
   - Problema: [formato confuso]
   - Mejora: [instrucción]

5. **Robustez** (¿Maneja errores?)
   - Score: X/5
   - Problema: [error no manejado]
   - Mejora: [instrucción]

TOTAL: XX/25

Si TOTAL >= 23/25: "NO_IMPROVEMENTS_NEEDED"
Si no, proporciona feedback detallado."""

DATA_REFINEMENT_PROMPT = """Mejora este código de análisis según feedback:

ARCHIVO CSV: {file_path}
TAREA: {task}

CÓDIGO ACTUAL:
```python
{output}
```

FEEDBACK:
{feedback}

HISTORIAL PREVIO:
{history}

Genera código mejorado (SOLO código):"""

# =============================================================================
# DEBUG PROMPTS
# =============================================================================

DEBUG_PROMPT = """Analiza y corrige este código con errores:

CÓDIGO CON ERROR:
```python
{code}
```

ERROR REPORTADO:
{error}

Proporciona:
1. **Diagnóstico**: ¿Qué causa el error exactamente?
2. **Ubicación**: ¿En qué línea/sección está el problema?
3. **Código Corregido**: (SOLO el código Python corregido)"""

DEBUG_EVALUATION_PROMPT = """Evalúa esta corrección de bug:

CÓDIGO ORIGINAL CON BUG:
```python
{original_code}
```

CÓDIGO CORREGIDO:
```python
{output}
```

RESULTADO DE EJECUCIÓN:
{exec_result}

Evalúa (1-5 puntos):

1. **Bug Corregido** (¿Se solucionó el error original?)
   - Score: X/5
   - Problema: [si persiste]
   - Mejora: [instrucción]

2. **Funcionalidad** (¿El código ahora funciona?)
   - Score: X/5
   - Problema: [si hay nuevo error]
   - Mejora: [instrucción]

3. **Sin Regresiones** (¿No se introdujeron nuevos bugs?)
   - Score: X/5
   - Problema: [nuevo bug detectado]
   - Mejora: [instrucción]

4. **Calidad** (¿La corrección es elegante?)
   - Score: X/5
   - Problema: [corrección fea]
   - Mejora: [instrucción]

5. **Completitud** (¿Se corrigieron TODOS los issues?)
   - Score: X/5
   - Problema: [issue pendiente]
   - Mejora: [instrucción]

TOTAL: XX/25

Si TOTAL >= 23/25: "NO_IMPROVEMENTS_NEEDED"
Si no, proporciona feedback."""

DEBUG_REFINEMENT_PROMPT = """Mejora la corrección según feedback:

CÓDIGO ORIGINAL CON BUG:
```python
{original_code}
```

TU CORRECCIÓN ACTUAL:
```python
{output}
```

FEEDBACK:
{feedback}

HISTORIAL:
{history}

Genera código corregido mejorado (SOLO código):"""
