# Error Translation Layer
# Converts technical Python errors into semantic instructions for LLM

import re
from typing import Optional


# Common error patterns and their semantic translations
ERROR_TRANSLATIONS = {
    # Index/Key errors
    "IndexError": {
        "pattern": r"IndexError:.*",
        "translation": "El índice excede los límites de la lista. Verifica que el índice sea < len(lista).",
        "fix_hint": "Usa range(len(lista)) o verifica límites antes de acceder."
    },
    "KeyError": {
        "pattern": r"KeyError:.*'(.+)'",
        "translation": "La clave '{0}' no existe en el diccionario. Verifica las claves disponibles.",
        "fix_hint": "Usa dict.get(key, default) o verifica 'if key in dict' primero."
    },
    
    # Import errors (muy común en nuestro sistema)
    "ModuleNotFoundError": {
        "pattern": r"ModuleNotFoundError:.*'(.+)'",
        "translation": "No puedes importar '{0}' porque no existe. Define la lógica inline en tu código.",
        "fix_hint": "NO uses 'from proyecto import X'. Define las funciones directamente."
    },
    "ImportError": {
        "pattern": r"ImportError:.*",
        "translation": "Error de importación. No intentes importar módulos del proyecto.",
        "fix_hint": "Usa solo imports de librería estándar (re, json, os) o define todo inline."
    },
    
    # Type errors
    "TypeError": {
        "pattern": r"TypeError:.*'(.+)'.*'(.+)'",
        "translation": "Tipos incompatibles: intentaste operar '{0}' con '{1}'.",
        "fix_hint": "Convierte los tipos antes de operar: int(), str(), list(), etc."
    },
    "TypeError_args": {
        "pattern": r"TypeError:.*takes (\d+).*but (\d+)",
        "translation": "La función espera {0} argumentos pero recibió {1}.",
        "fix_hint": "Verifica la firma de la función y pasa el número correcto de argumentos."
    },
    
    # Attribute errors
    "AttributeError": {
        "pattern": r"AttributeError:.*'(.+)'.*'(.+)'",
        "translation": "El objeto tipo '{0}' no tiene el atributo '{1}'.",
        "fix_hint": "Verifica el tipo del objeto y usa métodos que sí exista."
    },
    
    # Value errors
    "ValueError": {
        "pattern": r"ValueError:.*",
        "translation": "Valor inválido para la operación. Verifica el formato de los datos.",
        "fix_hint": "Valida los datos antes de procesar: comprueba formato, rango, tipo."
    },
    
    # Name errors (variable no definida)
    "NameError": {
        "pattern": r"NameError:.*'(.+)'",
        "translation": "La variable '{0}' no está definida. Declárala antes de usarla.",
        "fix_hint": "Define la variable antes de usarla o verifica el nombre (typo?)."
    },
    
    # Syntax errors
    "SyntaxError": {
        "pattern": r"SyntaxError:.*",
        "translation": "Error de sintaxis. Revisa paréntesis, comillas, dos puntos.",
        "fix_hint": "Verifica: () {} [] balanceados, : después de if/for/def, indentación."
    },
    
    # Recursion
    "RecursionError": {
        "pattern": r"RecursionError:.*",
        "translation": "Recursión infinita detectada. La función se llama sin caso base.",
        "fix_hint": "Agrega un caso base que retorne sin llamar a la función."
    },
    
    # File errors
    "FileNotFoundError": {
        "pattern": r"FileNotFoundError:.*'(.+)'",
        "translation": "El archivo '{0}' no existe. Verifica la ruta.",
        "fix_hint": "Usa rutas relativas al workspace o verifica que el archivo exista."
    },
    
    # Zero division
    "ZeroDivisionError": {
        "pattern": r"ZeroDivisionError:.*",
        "translation": "División por cero. El divisor es 0.",
        "fix_hint": "Verifica que el divisor no sea 0 antes de dividir."
    },
}


def translate_error(error_message: str) -> dict:
    """
    Translate a technical Python error into semantic instruction.
    
    Returns:
        dict with keys: original, translated, fix_hint, error_type
    """
    if not error_message:
        return {
            "original": "",
            "translated": "Error desconocido",
            "fix_hint": "Revisa el código completo",
            "error_type": "unknown"
        }
    
    # Try to match each error pattern
    for error_type, info in ERROR_TRANSLATIONS.items():
        match = re.search(info["pattern"], error_message)
        if match:
            # Format translation with captured groups
            groups = match.groups() if match.groups() else []
            try:
                translated = info["translation"].format(*groups)
                fix_hint = info["fix_hint"].format(*groups)
            except (IndexError, KeyError):
                translated = info["translation"]
                fix_hint = info["fix_hint"]
            
            return {
                "original": error_message[:200],
                "translated": translated,
                "fix_hint": fix_hint,
                "error_type": error_type.split("_")[0]  # Remove suffix like _args
            }
    
    # Fallback: extract error type from message
    error_type_match = re.match(r"(\w+Error):", error_message)
    error_type = error_type_match.group(1) if error_type_match else "Error"
    
    return {
        "original": error_message[:200],
        "translated": f"{error_type} encontrado. Revisa la lógica del código.",
        "fix_hint": "Analiza el traceback y corrige el problema específico.",
        "error_type": error_type
    }


def format_for_llm(error_message: str) -> str:
    """
    Format the error translation for injection into LLM prompt.
    Returns a structured, semantic error description.
    """
    result = translate_error(error_message)
    
    return f"""❌ ERROR: {result['error_type']}
📝 Problema: {result['translated']}
💡 Cómo arreglar: {result['fix_hint']}"""


# Quick test
if __name__ == "__main__":
    test_errors = [
        "IndexError: list index out of range",
        "ModuleNotFoundError: No module named 'utils.validators'",
        "KeyError: 'nombre'",
        "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        "NameError: name 'resultado' is not defined",
    ]
    
    print("=== Error Translation Layer Test ===\n")
    for err in test_errors:
        print(f"Original: {err}")
        print(format_for_llm(err))
        print("-" * 50)
