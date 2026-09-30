"""Herramienta para escribir resúmenes en Markdown en output/."""

from pathlib import Path

import tools.security as security
from tools.security import SecurityError, validate_path

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_summary",
        "description": (
            "Escribe un resumen en Markdown dentro de la carpeta output/. "
            "Solo permite archivos .md."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta del archivo .md dentro de output/. Ej: 'summary.md'.",
                },
                "content": {
                    "type": "string",
                    "description": "Contenido Markdown del resumen.",
                },
            },
            "required": ["path", "content"],
        },
    },
}


def write_summary(path: str, content: str) -> dict:
    """Escribe un archivo Markdown en output/.

    Solo permite archivos .md dentro de output/.
    """
    # Validar que termine en .md
    if not path.endswith(".md"):
        return {"error": "Solo se permiten archivos .md", "success": False}

    try:
        full_path = validate_path(path, security.OUTPUT_DIR)
    except SecurityError as e:
        return {"error": str(e), "success": False}

    try:
        security.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(full_path)}
    except Exception as e:
        return {"error": str(e), "success": False}