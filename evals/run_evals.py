"""Ejecuta evaluaciones comparando agents/triage.py y agents/baseline.py."""

import json
import os
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.triage import run_agent as run_triage
from agents.baseline import triage_reports as run_baseline


def run_evals():
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

    for case in cases:
        # Baseline
        baseline_output = run_baseline([case["report"]])
        # Triage
        try:
            triage_output, _ = run_triage(case["report"])
        except Exception:
            triage_output = {"results": [{"test": "error", "category": "ERROR", "confidence": 0, "reason": "Excepción", "evidence": ""}], "unknown": []}

        # Extraer resultados de triage (puede ser dict con results)
        triage_results = triage_output.get("results", []) if isinstance(triage_output, dict) else []
        triage_map = {}
        for r in triage_results:
            if isinstance(r, dict):
                key = r.get("test_name") or r.get("test", "unknown")
                triage_map[key] = r.get("category", r.get("type", "UNKNOWN"))

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

            # Confusión triage
            if actual_triage:
                confusion_triage.setdefault(actual_triage, {}).setdefault(expected_cat, 0)
                confusion_triage[actual_triage][expected_cat] += 1

            # Confusión baseline
            if actual_baseline:
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
    
    # Unknown rate
    unknown_count = sum(1 for r in triage_results if isinstance(r, dict) and r.get("category") == "UNKNOWN")
    unknown_rate = unknown_count / total_tests if total_tests > 0 else 0.0
    
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

    lines = [
        "# Resultados de Evaluación",
        f"Modelo usado: `{model}`",
        f"Fecha: {date_str}",
        "",
        f"## Comparación Triage vs Baseline ({total_tests} tests)",
        f"- **Triage (LLM)**: {correct_triage}/{total_tests} = {accuracy_triage:.2%}",
        f"- **Baseline (reglas)**: {correct_baseline}/{total_tests} = {accuracy_baseline:.2%}",
        f"- **Unknown rate (Triage)**: {unknown_rate:.2%}",
        "",
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
