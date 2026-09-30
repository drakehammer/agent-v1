"""Baseline: clasificador de reglas fijas (para comparación con triage)."""

from pathlib import Path
from tools.read_report import read_report


def classify_by_exception_type_and_message(test: dict) -> dict:
    """Clasifica mirando exception_type y message, no solo elemento XML."""
    msg = (test.get("message") or "").lower()
    kind = test.get("kind", test.get("type", "unknown"))
    name = test.get("test", "unknown")

    # BUG_REAL: valores incorrectos consistentes
    if "expected" in msg and ("but was" in msg or "expected" in msg):
        return {"test": name, "category": "BUG_REAL", "confidence": 0.92,
                "reason": "Aserción falla: valor devuelto distinto al esperado", "evidence": msg}

    # AMBIENTE: conexión, DNS, 5xx, credenciales
    if "connection refused" in msg or "unknown host" in msg or "timeout" in msg and "dns" in msg:
        return {"test": name, "category": "AMBIENTE", "confidence": 0.88,
                "reason": "Problema de infraestructura o configuración", "evidence": msg}
    if "503" in msg or "401" in msg or "500" in msg:
        return {"test": name, "category": "AMBIENTE", "confidence": 0.85,
                "reason": "Error del entorno (5xx o auth)", "evidence": msg}

    # FLAKY: intermitente, race, orden
    if "timeout" in msg and "after" in msg:
        return {"test": name, "category": "FLAKY", "confidence": 0.82,
                "reason": "Timeout intermitente / dependiente de tiempo", "evidence": msg}
    if "race" in msg or "concurrent" in msg:
        return {"test": name, "category": "FLAKY", "confidence": 0.85,
                "reason": "Race condition", "evidence": msg}
    if kind == "skipped" or "previous" in msg or "order" in msg:
        return {"test": name, "category": "FLAKY", "confidence": 0.75,
                "reason": "Dependencia de orden o datos compartidos", "evidence": msg}

    return {"test": name, "category": "UNKNOWN", "confidence": 0.3,
            "reason": "Evidencia insuficiente", "evidence": msg}


def triage_reports(report_paths: list[str]) -> list[dict]:
    results = []
    for report_path in report_paths:
        full_path = None
        # Resolver ruta con soporte para 'synthetic/x.xml', 'x.xml', 'data/samples/synthetic/x.xml'
        for base in [Path("data/samples/synthetic"), Path("data/samples/real"), Path(".")]:
            p = (base / report_path).resolve()
            if p.exists():
                full_path = p
                break
        if full_path is None:
            # Intentar con nombre directo
            p = Path(report_path).resolve()
            if p.exists():
                full_path = p

        if full_path is None or not full_path.exists():
            results.append({"test": str(report_path), "category": "NOT_FOUND",
                            "confidence": 0.0, "reason": "Archivo no encontrado",
                            "evidence": str(report_path)})
            continue

        try:
            failed = read_report(str(report_path))
        except Exception as e:
            results.append({"test": str(report_path), "category": "ERROR",
                            "confidence": 0.0, "reason": str(e), "evidence": str(e)})
            continue

        if not failed:
            # Reporte sin fallos
            results.append({"test": str(report_path), "category": "NONE",
                            "confidence": 1.0, "reason": "No hay tests fallidos",
                            "evidence": "Report vacío de fallas"})
            continue

        # Clasificar cada falla (devolver todos, no solo primero)
        for test in failed:
            results.append(classify_by_exception_type_and_message(test))
    return results