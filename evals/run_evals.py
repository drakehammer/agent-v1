"""Ejecuta evaluaciones del agente sobre casos sintéticos/real."""

import json
import os
from datetime import datetime
from pathlib import Path

# Importación del agente
from agents.triage import triage_reports


def run_evals():
    with open("evals/cases.json", encoding="utf-8") as f:
        cases = json.load(f)

    model = os.environ.get("AGENT_MODEL", "openrouter/free")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total = 0
    correct = 0
    confusion = {}
    category_stats = {}
    results = []

    for case in cases:
        output = triage_reports([case["report"]])
        actual = {}
        for item in output:
            if isinstance(item, dict) and "test" in item and "type" in item:
                actual[item.get("test")] = item.get("type")
            elif isinstance(item, dict) and "status" in item and item["status"] == "not_found":
                actual["missing"] = "missing"

        case_result = {
            "name": case["name"],
            "expected": case["expected"],
            "actual": actual,
        }
        results.append(case_result)

        # Comparar
        for test_name, expected_cat in case["expected"].items():
            total += 1
            actual_cat = actual.get(test_name)
            if actual_cat == expected_cat:
                correct += 1
            else:
                # Confusión
                if actual_cat not in confusion:
                    confusion[actual_cat] = {}
                confusion[actual_cat][expected_cat] = confusion[actual_cat].get(expected_cat, 0) + 1

        for cat in ["BUG_REAL", "FLAKY", "AMBIENTE"]:
            cat_total = sum(1 for c in cases for t in c["expected"] if c["expected"][t] == cat)
            cat_correct = sum(1 for r in results[-len(cases):] for test_name in r["expected"] if r["expected"][test_name] == cat and r["actual"].get(test_name) == cat)
            category_stats[cat] = {"total": cat_total, "correct": cat_correct}

    accuracy = correct / total if total > 0 else 0.0

    # Escribir resultados
    results_path = Path("evals/results.md")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Resultados de Evaluación",
        f"Modelo usado: `{model}`",
        f"Fecha: {date_str}",
        "",
        f"## Accuracy total: {accuracy:.2%} ({correct}/{total})",
        "",
        "## Por categoría",
    ]

    for cat in ["BUG_REAL", "FLAKY", "AMBIENTE"]:
        stats = category_stats.get(cat, {"total": 0, "correct": 0})
        cat_acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        lines.append(f"- **{cat}**: {stats['correct']}/{stats['total']} = {cat_acc:.2%}")

    lines.extend([
        "",
        "## Matriz de confusión (simplificada)",
        "| Actual \\ Esperado | BUG_REAL | FLAKY | AMBIENTE |",
        "|---|---|---|---|",
    ])

    for actual_cat in ["BUG_REAL", "FLAKY", "AMBIENTE", "unknown"]:
        row = [actual_cat]
        for expected_cat in ["BUG_REAL", "FLAKY", "AMBIENTE"]:
            count = confusion.get(actual_cat, {}).get(expected_cat, 0)
            row.append(str(count))
        lines.append("| " + " | ".join(row) + " |")

    lines.extend([
        "",
        "> Nota: los resultados son reales de ejecución del agente con el modelo configurado.",
    ])

    results_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    run_evals()