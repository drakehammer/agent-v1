"""Herramienta para leer reportes JUnit XML (Maven Surefire)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from defusedxml import ElementTree as DefusedET

from tools.security import DATA_DIR, SecurityError, validate_path

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_report",
        "description": (
            "Lee un archivo JUnit XML en formato Maven Surefire y devuelve "
            "la lista de tests fallidos con nombre (clase.metodo), tipo de fallo, "
            "mensaje, stacktrace (max 40 líneas), exception_type del atributo type, "
            "y contenido de system-out / system-err. No incluye skipped como fallo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al archivo JUnit XML, relativa a data/samples/ (ej: 'synthetic/x.xml', 'x.xml', 'data/samples/synthetic/x.xml').",
                }
            },
            "required": ["path"],
        },
    },
}


def _resolve_path(path: str) -> Path:
    # Resolver rutas: 'synthetic/x.xml', 'x.xml', 'data/samples/synthetic/x.xml'
    candidates = [
        Path(path),
        Path("data/samples/synthetic") / path,
        Path("data/samples/real") / path,
        Path("data/samples/synthetic") / Path(path).name,
        Path("data/samples/real") / Path(path).name,
    ]
    for c in candidates:
        resolved = c.resolve()
        if resolved.exists():
            # Validar que esté dentro de DATA_DIR
            try:
                resolved.relative_to(DATA_DIR.resolve())
                return resolved
            except ValueError:
                continue
    # Si no se encuentra, lanzar excepción
    raise SecurityError(f"Archivo no encontrado (o fuera de datos): {path}")


def read_report(path: str) -> list[dict]:
    full_path = _resolve_path(path)
    # Usar defusedxml para evitar XXE
    tree = DefusedET.parse(str(full_path))
    root = tree.getroot()
    failures = []

    # Leer system-out y system-err del suite para contexto
    suite_output = ""
    suite_err = ""
    for so in root.findall(".//system-out"):
        suite_output += (so.text or "") + "\n"
    for se in root.findall(".//system-err"):
        suite_err += (se.text or "") + "\n"

    suites = root.findall(".//testsuite")
    if not suites and root.tag == "testsuite":
        suites = [root]

    for suite in suites:
        for testcase in suite.findall("testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            full_name = f"{classname}.{name}" if classname else name

            failure_elem = testcase.find("failure")
            error_elem = testcase.find("error")

            # No incluir skipped como fallo
            skipped_elem = testcase.find("skipped")
            if skipped_elem is not None:
                continue

            entry = {
                "test": full_name,
                "classname": classname,
                "name": name,
                "kind": None,
                "message": "",
                "exception_type": "",
                "stacktrace": "",
                "system_out": suite_output[:2000],
                "system_err": suite_err[:2000],
            }

            if failure_elem is not None:
                entry["kind"] = "failure"
                entry["message"] = failure_elem.get("message", "") or (failure_elem.text or "")
                entry["exception_type"] = failure_elem.get("type", "")
                entry["stacktrace"] = _extract_stacktrace(failure_elem, 40)
                failures.append(entry)
            elif error_elem is not None:
                entry["kind"] = "error"
                entry["message"] = error_elem.get("message", "") or (error_elem.text or "")
                entry["exception_type"] = error_elem.get("type", "")
                entry["stacktrace"] = _extract_stacktrace(error_elem, 40)
                failures.append(entry)

    return failures


def _extract_stacktrace(elem, max_lines: int = 40) -> str:
    text = (elem.text or "")
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"... ({len(text.splitlines())} líneas totales)")
    return "\n".join(lines)