# Guía de Ejecución Autónoma y Supervisión

Este documento detalla cómo el Agente (Antigravity/Gemini) puede ejecutar tareas de larga duración de manera autónoma, supervisando scripts locales sin bloquear la interfaz del usuario ni requerir aprobación constante.

## 1. El Patrón "Background & Monitor"

Para iterar durante horas (ej. entrenar un modelo, correr tests masivos, o el script `night_school.py`), **NO** uses una sesión interactiva de PowerShell que requiera inputs constantes.

### ✅ La Forma Correcta: Async `run_command` + `command_status`

1.  **Lanzar el proceso en background:**
    Usa la herramienta `run_command` y asegúrate de recibir un `CommandId`.
    ```python
    # Ejemplo conceptual
    run_command("python sandbox/night_school.py", wait_ms_before_async=2000)
    ```
    *Nota: `wait_ms_before_async` bajo (e.g. 1000-2000ms) asegura que el comando se vaya al fondo rápido.*

2.  **Monitorear con `command_status`:**
    No te quedes esperando el resultado final. Haz "ping" periódicos.
    ```python
    command_status(command_id=CID_DEL_PASO_1, wait_duration_seconds=60)
    ```
    *   Si el status es `RUNNING`, el agente puede decidir esperar más y volver a llamar `command_status`, o hacer otras tareas mientras.
    *   Esto permite bucles de supervisión de 8+ horas como se demostró en la sesión "Night School".

3.  **Leer Logs en Archivos:**
    En lugar de depender solo del stdout de `command_status`, configura tu script para escribir en un archivo `.log` (ej. `night_school.log`).
    *   Usa `view_file` o `tail` (si existiera) para leer el progreso real.
    *   Esto evita problemas de buffer o truncado en la salida del comando.

## 2. 🚫 AVOID: Powershell Interactivo

*   **Evita:** `powershell.exe -Command "..."` si esperas interactuar con el stdin.
*   **Peligro:** Si el comando pide confirmación ("Press Any Key"), el agente se quedará colgado (Hang).
*   **Solución:** Pasa argumentos de "no interacción" (ej. `-y`, `--no-input`) a los scripts que ejecutes.

## 3. Control y "Safety Brakes"

Durante una ejecución autónoma, el agente supervisor debe tener criterios claros para abortar:

1.  **Safety Brake (Freno de Seguridad):**
    Si detectas >3 fallos consecutivos en los logs (ej. reading `night_school.log`), detén el proceso.
    *   Usa `send_command_input(terminate=True)` para matar el proceso de fondo.
2.  **Timeouts:**
    Define un tiempo máximo (ej. "Hasta las 9 AM"). Verifica la hora local en cada ciclo de monitoreo.

## 4. Ejemplo de "Prompt Mental" para el Agente Supervisor

Si el usuario pide "Trabaja toda la noche en esto", tu plan debe ser:
1.  START: `run_command("python script.py > output.log")`
2.  LOOP:
    *   `command_status()` (Check if alive)
    *   `view_file("output.log")` (Check progress)
    *   Analyze: ¿Todo bien? -> Continue. ¿Error crítico? -> Stop.
    *   Sleep/Wait (implícito en el turno del agente).

---
## 5. Protocolo de Auto-Reparación y Mejora (Self-Repair)

El Agente tiene **AUTONOMÍA TOTAL** para modificar el sistema `self-refine-cli` si esto es necesario para cumplir su misión (ej. arreglar un bug, superar un bloqueo).

### Permisos Explícitos
*   ✅ **Modificar Código Base:** Puede editar archivos en `core/`, `tools/`, `memory/` si encuentra bugs o limitaciones.
*   ✅ **Crear Herramientas:** Si una tarea es imposible con las herramientas actuales, el Agente debe **crear una nueva herramienta** en `tools/` y registrarla.
*   ✅ **Detener Procesos:** Si un script (ej. `night_school.py`) está fallando o se necesita reiniciar el entorno para cargar nuevas herramientas, el Agente debe detenerlo (`terminate=True`), aplicar los cambios, y volver a lanzarlo.

### El Ciclo de Super-Mejora (Meta-Loop)
Cuando el Agente actúa como Supervisor/Ingeniero, debe seguir este bucle iterativo:

1.  **Diagnóstico (Logs & Debugger):**
    *   Leer `outputs/sessions/*.json` para ver el "pensamiento" crudo del modelo.
    *   ¿El fallo fue por alucinación? ¿Falta de herramienta? ¿Crash de Python?

2.  **Acción Correctiva:**
    *   **Si es Alucinación de Parámetros:** Modificar el `description` de la herramienta en `tools/` para ser más explícito, o ajustar el Prompt del Sistema.
    *   **Si falta Capacidad:** Programar una nueva herramienta (ej. `ApplyPatchTool`).
    *   **Si es Error de Entorno:** Arreglar imports, instalar dependencias (simuladas), o crear directorios.

3.  **Verificación (Test):**
    *   Crear un script de prueba aislado (ej. `sandbox/test_fix.py`).
    *   Ejecutarlo y verificar que la mejora funciona.

4.  **Despliegue:**
    *   Reiniciar el proceso principal con la mejora aplicada.

**Regla de Oro:** No te detengas ante un error. Úsalo como señal para mejorar el sistema. Si el sistema no te deja leer un archivo, arregla el sistema de archivos. Si no te deja ejecutar, arregla el ejecutor.
