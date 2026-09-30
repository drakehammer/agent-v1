"""Herramienta para leer reportes JUnit XML.

Soporta formato Maven Surefire: elements testsuite, testcase, failure, error,
skipped y system-out.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from tools.security import DATA_DIR, SecurityError, validate_path

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_report",
        "description": (
            "Lee un archivo JUnit XML en formato Maven Surefire y devuelve "
            "la lista de tests fallidos con nombre, clase, tipo de fallo, mensaje "
            "y stacktrace resumido (máximo 40 líneas por test). "
            "Busca en data/samples/real/ o data/samples/synthetic/."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Nombre o ruta del archivo JUnit XML dentro de data/samples/. Ej: 'synthetic/test1.xml' o 'test1.xml'.",
                }
            },
            "required": ["path"],
        },
    },
}


def _find_report(path: str) -> Path | None:
    """Busca el archivo en data/samples/, data/samples/synthetic/ y data/samples/real/."""
    # Try exact path first
    try:
        full_path = validate_path(f"samples/{path}", DATA_DIR)
        if full_path.exists():
            return full_path
    except SecurityError:
        pass

    # Try synthetic/
    try:
        full_path = validate_path(f"samples/synthetic/{path}", DATA_DIR)
        if full_path.exists():
            return full_path
    except SecurityError:
        pass

    # Try real/
    try:
        full_path = validate_path(f"samples/real/{path}", DATA_DIR)
        if full_path.exists():
            return full_path
    except SecurityError:
        pass

    return None


def read_report(path: str) -> list[dict]:
    """Lee un JUnit XML y devuelve los tests fallidos.

    Un test está considerado fallido si tiene un elemento <failure>, <error>
    o <skipped>.
    """
    full_path = _find_report(path)

    if full_path is None:
        # Check for security violation (path traversal)
        try:
            validate_path(f"samples/{path}", DATA_DIR)
        except SecurityError as e:
            return [{"error": str(e), "type": "security"}]
        return [{"error": f"Archivo no encontrado: {path}", "type": "file_not_found"}]

    try:
        tree = ET.parse(full_path)
    except ET.ParseError as e:
        return [{"error": f"Error parsing XML: {e}", "type": "parse_error"}]

    root = tree.getroot()
    failures = []

    # Soportar <testsuites> >> <testsuite> o <testsuite> directamente
    suites = root.findall(".//testsuite")
    if not suites and root.tag == "testsuite":
        suites = [root]

    for suite in suites:
        suite_name = suite.get("name", "unknown")

        for testcase in suite.findall("testcase"):
            test_name = testcase.get("name", "unknown")
            classname = testcase.get("classname", suite_name)
            full_test_name = f"{classname}.{test_name}" if classname != suite_name else test_name

            failure_elem = testcase.find("failure")
            error_elem = testcase.find("error")
            skipped_elem = testcase.find("skipped")

            entry = {
                "test": full_test_name,
                "classname": classname,
                "name": test_name,
            }

            if failure_elem is not None:
                entry["type"] = "failure"
                entry["message"] = failure_elem.get("message", "") or failure_elem.text or ""
                entry["stacktrace"] = _extract_stacktrace(failure_elem, 40)
                failures.append(entry)
            elif error_elem is not None:
                entry["type"] = "error"
                entry["message"] = error_elem.get("message", "") or error_elem.text or ""
                entry["stacktrace"] = _extract_stacktrace(error_elem, 40)
                failures.append(entry)
            elif skipped_elem is not None:
                entry["type"] = "skipped"
                entry["message"] = skipped_elem.get("message", "") or ""
                entry["stacktrace"] = ""
                failures.append(entry)

    return failures


def _extract_stacktrace(elem: ET.Element, max_lines: int = 40) -> str:
    """Extrae el stacktrace de un elemento de fallo/error, limitado a max_lines."""
    text = elem.text or ""
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"... ({len(text.split(chr(10)))} líneas totales)")
    return "\n".join(lines)