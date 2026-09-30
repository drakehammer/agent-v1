"""Agente principal de triage de tests automatizados.

Clasifica tests fallidos en BUG_REAL, FLAKY o AMBIENTE basándose en el análisis de reportes JUnit XML.
"""

import json
from pathlib import Path

from tools.read_report import read_report
from tools.read_test import read_test
from tools.write_summary import write_summary

# Configuración del output
OUTPUT_DIR = Path("/some/default/path")  # Se modificará dinámicamente


def triage_reports(report_paths: list[str]) -> dict:
    """
    Analiza múltiples reportes JUnit XML y clasifica los tests fallidos.

    Args:
        report_paths: Lista de rutas a archivos de reporte JUnit XML.

    Returns:
        Diccionario con resultados clasificados.
    """
    results = []

    for report_path in report_paths:
        try:
            # Leer el reporte
            if "synthetic/" in report_path or "real/" in report_path:
                # Buscar en las carpetas de muestras
                samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples"
                samples_dir.mkdir(parents=True, exist_ok=True)
                
                # Buscar el archivo en las carpetas apropiadas
                found = False
                for subdir in ["synthetic", "real"]:
                    candidate = samples_dir / subdir / Path(report_path)
                    if candidate.exists():
                        found = True
                        break
                
                if not found:
                    # Si no se encuentra, intentar buscar directamente
                    full_path = Path(report_path)
                    if full_path.exists():
                        found = True
                
                if not found:
                    results.append({
                        "path": str(report_path),
                        "status": "not_found",
                        "confidence": 0.0,
                        "reason": "Archivo no encontrado",
                        "error": "Archivo no encontrado"
                    })
                    continue

                # Leer el reporte
                try:
                    report = read_report(str(full_path))
                except Exception as e:
                    results.append({
                        "path": str(full_path),
                        "status": "error",
                        "confidence": 0.0,
                        "reason": str(e),
                        "error": str(e)
                    })
                    continue

                # Clasificar el test
                categorized = categorize_test(report)
                results.append(categorized)

        except Exception as e:
            results.append({
                "path": str(report_path),
                "status": "error",
                "confidence": 0.0,
                "reason": str(e),
                "error": str(e)
            })

    return results


def categorize_test(report: list[dict]) -> dict:
    """
    Clasifica un único reporte JUnit XML en BUG_REAL, FLAKY o AMBIENTE.

    Args:
        report: Lista de tests fallidos del reporte.

    Returns:
        Diccionario con la clasificación del test.
    """
    for test in report:
        test_type = test.get("type", "unknown")
        
        # Prioridad: BUG_REAL > FLAKY > AMBIENTE
        if test_type == "failure":
            return {
                "test": test.get("name", "unknown"),
                "classname": test.get("classname", "unknown"),
                "type": "BUG_REAL",
                "confidence": 0.95,
                "reason": "Fallo de assertion o error en el test"
            }
        elif test_type == "error":
            return {
                "test": test.get("name", "unknown"),
                "classname": test.get("classname", "unknown"),
                "type": "ERROR",
                "confidence": 0.95,
                "reason": "Error en el test (ej. Connection refused, timeouts)"
            }
        elif test_type == "skipped":
            return {
                "test": test.get("name", "unknown"),
                "classname": test.get("classname", "unknown"),
                "type": "SKIPPED",
                "confidence": 0.8,
                "reason": "Test marcado como skipped"
            }
        else:
            # Para cualquier otro tipo, asumir que es un flaky
            return {
                "test": test.get("name", "unknown"),
                "classname": test.get("classname", "unknown"),
                "type": "FLAKY",
                "confidence": 0.7,
                "reason": "Posible flakiness (depende de condiciones externas)"
            }


def main():
    """Punto de entrada principal."""
    # Ejemplo de uso: analizar reportes de la carpeta data/samples/
    report_paths = [
        "data/samples/synthetic/test_failure.xml",
        "data/samples/synthetic/test_error.xml",
        "data/samples/synthetic/test_skipped.xml",
        "data/samples/synthetic/test_ok.xml",
    ]
    
    results = triage_reports(report_paths)
    
    # Generar resumen
    summary = {
        "total": len(results),
        "by_type": {
            "BUG_REAL": sum(1 for r in results if r.get("type") == "BUG_REAL"),
            "FLAKY": sum(1 for r in results if r.get("type") == "FLAKY"),
            "AMBIENTE": sum(1 for r in results if r.get("type") == "AMBIENTE"),
            "SKIPPED": sum(1 for r in results if r.get("type") == "SKIPPED"),
            "NOT_FOUND": sum(1 for r in results if r.get("status") == "not_found"),
            "ERROR": sum(1 for r in results if r.get("status") == "error"),
        },
        "details": results
    }
    
    # Escribir resumen
    write_summary("summary.md", json.dumps(summary, indent=2))
    
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()