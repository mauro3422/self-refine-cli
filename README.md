# 🚀 Self-Refine CLI

Agente autónomo de programación basado en la arquitectura **Self-Refine** del paper original.

## 🧠 Arquitectura

Basado en el paper [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651):

```
INPUT → GENERATE → FEEDBACK → REFINE → ... → OUTPUT ÓPTIMO
           ↑                      ↓
           └──────────────────────┘
                (iterativo)
```

### Componentes Clave (del paper)

1. **FEEDBACK**: Evalúa el output con scoring multi-dimensional
   - Localiza problemas específicos
   - Da instrucciones accionables de mejora

2. **REFINE**: Mejora basándose en el feedback
   - Retiene historial de intentos anteriores
   - Evita repetir errores

3. **STOPPING**: Se detiene cuando score ≥ 22/25

## ✨ Características

### 🔧 Herramientas Autónomas
El agente puede usar herramientas **por su cuenta**:
- `read_file` - Leer archivos
- `write_file` - Escribir archivos
- `list_dir` - Listar directorios
- `run_command` - Ejecutar comandos
- `python_exec` - Ejecutar Python

Durante el refinamiento, si detecta que necesita más información, **usa las herramientas automáticamente**.

### 💾 Memoria Persistente
Aprende de sus errores automáticamente:
- Cuando el score mejora significativamente, guarda qué aprendió
- Cuando no usa herramientas que debía, lo recuerda
- Las lecciones persisten entre sesiones

### 📊 Evaluación Multi-dimensional
Cada respuesta se evalúa en 5 dimensiones (1-5 puntos cada una):
1. Uso de herramientas
2. Precisión
3. Completitud
4. Claridad
5. Utilidad

## 🚀 Uso

### Modo Interactivo (Recomendado)
```bash
python main.py
```

### Comandos Especiales
- `help` - Ver ayuda
- `tools` - Ver herramientas disponibles
- `memory` - Ver estadísticas de memoria
- `clear` - Limpiar historial
- `exit` - Salir

### Modo Test
```bash
python test_agent.py "lee README.md y resúmelo"
```

## 📁 Estructura

```
self-refine-cli/
├── main.py              # Punto de entrada
├── test_agent.py        # Script de testing
├── config/
│   └── settings.py      # Configuración
├── core/
│   ├── agent.py         # Agente con Self-Refine
│   ├── llm_client.py    # Cliente LM Studio
│   ├── refiner.py       # Bucle de refinamiento
│   └── executor.py      # Ejecución de código
├── tools/               # Herramientas del agente
│   ├── base.py
│   ├── registry.py
│   ├── file_tools.py
│   └── command_tools.py
├── modules/             # Módulos especializados
├── prompts/             # Templates de prompts
├── utils/
│   ├── memory.py        # Memoria persistente
│   └── logger.py
├── sandbox/             # Workspace del agente
└── outputs/             # Logs y memoria
```

## 🔬 Basado en Investigación

### Paper Principal
- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
- [Website](https://selfrefine.info)
- [GitHub](https://github.com/madaan/self-refine)

### Conceptos Clave del Paper

**Feedback Accionable** (dos partes):
1. Localización del problema
2. Instrucción de mejora

Ejemplo del paper para código:
```
# wrong! The cost of a cup is not the same as the plate.
# So we need to calculate the cost of a cup first...
```

**Scoring por Tarea**:
| Tarea | Dimensiones | Total |
|-------|-------------|-------|
| Acronym | Pronunciation, Spelling, Relation, Connotation, Well-known | /25 |
| Dialogue | Relevant, Informative, Interesting, etc. | /30 |
| Code | Step-by-step verification | Pass/Fail |

### Inspiración Adicional
- **Poetiq**: Meta-sistema con auto-refinamiento adaptativo
- **ReAct**: Synergizing Reasoning and Acting in LLMs

## ⚙️ Configuración

Edita `config/settings.py`:
```python
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "lfm2"
MAX_TOKENS = 16000
SCORE_THRESHOLD = 22  # Mínimo para considerar respuesta óptima
```

## 📝 Ejemplo de Uso

```
🧑 Tú: lee el archivo main.py y dime qué hace

🤔 Procesando...
  📋 Tools sugeridas: ['read_file']
  🔧 read_file(main.py)
  ✅ OK (2345 chars)
  🔄 Self-Refine...
  📊 Score: 24/25 ✨

🤖 Agente:
El archivo main.py es el punto de entrada del CLI...
```

## 🧪 Testing

```bash
# Test individual
python test_agent.py "tu pregunta"

# Tests predefinidos
python test_agent.py
```

## 📄 Licencia

MIT
