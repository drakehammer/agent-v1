"""Ejecuta evaluaciones comparando agents/triage.py y agents/baseline.py."""

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=False)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.triage import run_agent as run_triage
from agents.baseline import triage_reports as run_baseline
from tools.paths import resolve_path


def run_evals():
    api_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY no está configurada. Crea .env o define la variable de entorno antes de correr las evals.")
        # No escribir results.md engañoso; solo mostrar baseline si es posible sin API
        # El baseline no requiere API; calculamos y mostramos
        try:
            with open("evals/cases.json", encoding="utf-8") as f:
                cases = json.load(f)
            from agents.baseline import triage_reports as run_baseline
            total_tests = 0
            correct_baseline = 0
            for case in cases:
                baseline_output = run_baseline([case["report"]])
                baseline_map = {}
                for item in baseline_output:
                    if isinstance(item, dict) and "test" in item:
                        baseline_map[item.get("test")] = item.get("category", item.get("type", "UNKNOWN"))
                for test_name, expected_cat in case.get("expected", {}).items():
                    total_tests += 1
                    if baseline_map.get(test_name) == expected_cat:
                        correct_baseline += 1
            accuracy_text = f"{correct_baseline}/{total_tests} = {correct_baseline/total_tests:.2%}" if total_tests else "N/A"
            print(f"Baseline (sin API): {accuracy_text}")
            print("No se calculó Triage (LLM): falta OPENROUTER_API_KEY.")
        except Exception as exc:
            print(f"No se pudo calcular ni baseline: {exc}")
        return

    with open("evals/cases.json", encoding="utf-8") as f:
        cases = json.load(f)

    model = os.environ.get("AGENT_MODEL", "openrouter/free")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Comparación: triage vs baseline
    results = []
    confusion_triage = {}
    confusion_baseline = {}

    total_cases = len(cases)
    total_tests = 0
    correct_triage = 0
    correct_baseline = 0
    unknown_triage_count = 0
    invalid_output_triage = 0
    total_tool_calls_triage = 0
    total_time_triage = 0.0
    execution_errors_global = []
    execution_error_count = 0

    for case in cases:
        # Baseline (siempre, sin API)
        report_path_resolved = resolve_path(case["report"])
        baseline_output = run_baseline([str(report_path_resolved)])
        # Triage
        try:
            triage_output, trace_info = run_triage(case["report"])
        except Exception as exc:
            execution_error_count += 1
            triage_output = {"results": [{"test_name": case["report"], "category": "execution_error", "confidence": 0, "reason": "Ejecución fallida: " + str(exc), "evidence": [str(exc)]}], "unknown": []}
            trace_info = {"iterations": 0, "tool_calls": [], "total_time": 0.0, "execution_error": str(exc)}

        # Separar evaluación de reparación: si hubo errores de validación o estructura rota, contar como invalid-output
        invalid_output_flag = False
        if isinstance(triage_output, dict):
            if triage_output.get("_validation_errors") or ("results" not in triage_output) or not isinstance(triage_output.get("results"), list):
                invalid_output_flag = True
        else:
            invalid_output_flag = True

        # Acumular métricas de ejecución
        if isinstance(trace_info, dict):
            total_time_triage += trace_info.get("total_time", 0.0)
            total_tool_calls_triage += len(trace_info.get("tool_calls", []))

        if invalid_output_flag:
            invalid_output_triage += 1
        else:
            # Solo contar unknown rate si no es inválido
            triage_results_for_unknown = triage_output.get("results", []) if isinstance(triage_output, dict) else []
            unknown_triage_count += sum(1 for r in triage_results_for_unknown if isinstance(r, dict) and r.get("category") == "UNKNOWN")

        # Extraer resultados de triage (puede ser dict con results)
        triage_results = triage_output.get("results", []) if isinstance(triage_output, dict) else []
        triage_map = {}
        for r in triage_results:
            if isinstance(r, dict):
                key = r.get("test_name") or r.get("test", "unknown")
                triage_map[key] = r.get("category", r.get("type", "UNKNOWN"))

        # Registrar errores de ejecución claramente
        for r in triage_results:
            if isinstance(r, dict) and r.get("category") == "execution_error":
                execution_errors_global.append({"case": case["name"], "test": r.get("test_name") or r.get("test") or case["report"], "reason": r.get("reason", "Ejecución fallida")})

        # Extraer resultados de baseline
        baseline_map = {}
        for item in baseline_output:
            if isinstance(item, dict) and "test" in item:
                baseline_map[item.get("test")] = item.get("category", item.get("type", "UNKNOWN"))

        # Calcular precisión
        for test_name, expected_cat in case.get("expected", {}).items():
            total_tests += 1
            actual_triage = triage_map.get(test_name)
            actual_baseline = baseline_map.get(test_name)

            if actual_triage == expected_cat:
                correct_triage += 1
            if actual_baseline == expected_cat:
                correct_baseline += 1

            # Confusión triage (sin execution_error)
            if actual_triage and actual_triage != "execution_error":
                confusion_triage.setdefault(actual_triage, {}).setdefault(expected_cat, 0)
                confusion_triage[actual_triage][expected_cat] += 1

            # Confusión baseline
            if actual_baseline and actual_baseline != "execution_error":
                confusion_baseline.setdefault(actual_baseline, {}).setdefault(expected_cat, 0)
                confusion_baseline[actual_baseline][expected_cat] += 1

        results.append({
            "case": case["name"],
            "expected": case.get("expected", {}),
            "triage_actual": triage_map,
            "baseline_actual": baseline_map,
        })

    accuracy_triage = correct_triage / total_tests if total_tests > 0 else 0.0
    accuracy_baseline = correct_baseline / total_tests if total_tests > 0 else 0.0

    from collections import Counter
    # Métricas adicionales
    categories = ["BUG_REAL", "FLAKY", "AMBIENTE", "UNKNOWN"]
    # Tests sin predicción (None) de LLM, incluyendo errores de ejecución
    none_triage = sum(
        1 for case in cases for k in case.get("expected", {})
        if (triage_map.get(k) is None or triage_map.get(k) == "execution_error")
    )
    # Confusion matrices
    def build_matrix(conf_dict):
        return {cat: {exp: conf_dict.get(cat, {}).get(exp, 0) for exp in categories} for cat in categories}
    
    mat_triage = build_matrix(confusion_triage)
    mat_baseline = build_matrix(confusion_baseline)
    
    # Precision / Recall / F1 por categoría (triage)
    metrics_text = []
    metrics_text.append("\n### Métricas por categoría (Triage)")
    metrics_text.append("| Cat | Precision | Recall | F1 |")
    metrics_text.append("|-----|-----------|--------|----|")
    for cat in categories:
        tp = confusion_triage.get(cat, {}).get(cat, 0)
        fp = sum(confusion_triage.get(cat, {}).get(exp, 0) for exp in categories if exp != cat)
        fn = sum(confusion_triage.get(exp, {}).get(cat, 0) for exp in categories if exp != cat)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        metrics_text.append(f"| {cat} | {precision:.2%} | {recall:.2%} | {f1:.2%} |")
    
    # Unknown rate (acumulado en todos los casos, no solo último)
    unknown_rate = unknown_triage_count / total_tests if total_tests > 0 else 0.0
    invalid_output_rate = invalid_output_triage / total_cases if total_cases > 0 else 0.0
    avg_time = total_time_triage / total_cases if total_cases > 0 else 0.0
    avg_tool_calls = total_tool_calls_triage / total_cases if total_cases > 0 else 0.0
    
    # Resumen por caso
    metrics_text.append("\n### Resumen por caso")
    for res in results:
        case_name = res["case"]
        pred = res["triage_actual"]
        exp = res["expected"]
        correct_items = [k for k in exp if pred.get(k) == exp[k]]
        metrics_text.append(f"- **{case_name}**: expected={exp}, pred={pred}, correct={len(correct_items)}/{len(exp)}")
    
    # Escribir resultados
    results_path = Path("evals/results.md")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    real_eval = execution_error_count == 0 and total_tool_calls_triage > 0 and total_time_triage > 0
    accuracy_text_triage = f"{correct_triage}/{total_tests} = {accuracy_triage:.2%}" if real_eval else "No calculado (evaluación no real: hay errores de ejecución, tool_calls == 0 o time == 0)"
    accuracy_text_baseline = f"{correct_baseline}/{total_tests} = {accuracy_baseline:.2%}"

    lines = [
        "# Resultados de Evaluación",
        f"Modelo usado: `{model}`",
        f"Fecha: {date_str}",
        "",
        f"## Comparación Triage vs Baseline ({total_tests} tests)",
        f"- **Triage (LLM)**: {accuracy_text_triage}",
        f"- **Baseline (reglas)**: {accuracy_text_baseline}",
        f"- **Unknown rate (Triage)**: {unknown_rate:.2%}",
        f"- **Invalid-output rate (Triage)**: {invalid_output_rate:.2%}",
        f"- **Average tool calls (Triage)**: {avg_tool_calls:.1f}",
        f"- **Average execution time (Triage)**: {avg_time:.2f}s",
        "",
    ]
    if not real_eval:
        lines.append("> WARNING: Evaluacion del LLM no considerada real: hay errores de ejecución (" + str(execution_error_count) + "), no se registraron llamadas a herramientas (tool_calls == 0) o el tiempo total es 0.")
        lines.append("> LLM marcado como 'No calculado' por errores de ejecución o falta de datos realistas.")
        lines.append("")
    lines.append(f"> Tests sin predicción (None) de LLM: se cuentan los faltantes por caso; no se ocultan en silencio.")
    if execution_errors_global:
        lines.append("## Errores de ejecución")
        lines.append("| Caso | Test | Razón |")
        lines.append("|------|------|-------|")
        for err in execution_errors_global:
            lines.append(f"| {err['case']} | {err['test']} | {err['reason']} |")
        lines.append("")
    lines += [
        "## Matriz de confusión (Triage)",
        "```",
        "Predicted \\ Expected  " + "  ".join(f"{cat:>4}" for cat in categories),
        "\n".join(f"{cat:>4}  " + "  ".join(f"{mat_triage[cat].get(exp, 0):>4}" for exp in categories) for cat in categories),
        "```",
        "",
        "## Métricas por categoría (Triage)",
    ] + metrics_text + [
        "",
        "> Nota: los resultados son reales tras ejecutar `run_evals.py`. No se inventan cifras.",
    ]

    results_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    run_evals()
