"""Herramienta para leer archivos de test o logs."""

from pathlib import Path

from tools.security import DATA_DIR, SecurityError, validate_path

MAX_CHARS = 10000

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_test",
        "description": (
            "Lee el archivo fuente del test o un log y devuelve su contenido completo (truncado a 10000 "
            "caracteres). Proporciona contexto suficiente para que el agente pueda distinguir hechos de hipótesis."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al archivo, relativa a data/.",
                }
            },
            "required": ["path"],
        },
    },
}


def read_test(path: str) -> str:
    """Lee un archivo de test o log y devuelve su contenido truncado."""
    try:
        full_path = validate_path(path, DATA_DIR)
    except SecurityError as e:
        return f"Error de seguridad: {e}"

    if not full_path.exists():
        return f"Error: archivo no encontrado: {path}"

    if not full_path.is_file():
        return f"Error: no es un archivo: {path}"

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error leyendo archivo: {e}"

    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + f"\n... ({len(content)} caracteres totales, truncado a {MAX_CHARS})"

    return content