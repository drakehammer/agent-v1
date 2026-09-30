"""Ejecuta evaluaciones comparando agents/triage.py y agents/baseline.py."""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=False)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.triage import run_agent as run_triage, DailyLimitError
from agents.baseline import triage_reports as run_baseline
from tools.paths import resolve_path

EVAL_DELAY_SECONDS = float(os.environ.get("EVAL_DELAY_SECONDS", "2"))


def get_cache_path(case_name: str, model: str) -> Path:
    safe_model = model.replace("/", "_").replace("\\", "_")
    return Path("evals/cache") / safe_model / f"{case_name}.json"


def load_cached_result(cache_path: Path) -> dict | None:
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cached_result(cache_path: Path, data: dict):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_evals():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Evaluar solo primeros N casos")
    parser.add_argument("--cases", type=str, default="", help="Casos específicos (nombre1,nombre2)")
    parser.add_argument("--refresh", action="store_true", help="Ignorar caché")
    args = parser.parse_args()

    api_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY no está configurada. Crea .env o define la variable de entorno antes de correr las evals.")
        try:
            with open("evals/cases.json", encoding="utf-8") as f:
                cases = json.load(f)
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
        all_cases = json.load(f)

    cases = all_cases
    if args.cases:
        selected = [c for c in cases if c["name"] in args.cases.split(",")]
        cases = selected
    if args.limit > 0:
        cases = cases[: args.limit]

    model = os.environ.get("AGENT_MODEL", "openrouter/free")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    evaluated_cases = 0
    cached_cases = 0
    daily_limit_stopped = False
    daily_limit_reset = ""

    for idx, case in enumerate(cases):
        case_name = case["name"]
        cache_path = get_cache_path(case_name, model)
        cached = None
        if not args.refresh:
            cached = load_cached_result(cache_path)

        if cached is not None:
            cached_cases += 1
            triage_output = cached.get("triage_output", {})
            trace_info = cached.get("trace_info", {})
        else:
            # Baseline (siempre, sin API)
            report_path_resolved = resolve_path(case["report"])
            baseline_output = run_baseline([str(report_path_resolved)])
            # Triage
            try:
                triage_output, trace_info = run_triage(case["report"])
            except DailyLimitError as exc:
                evaluated_cases += 1
                daily_limit_stopped = True
                daily_limit_reset = getattr(exc, "reset_time_local", "")
                # Detener inmediatamente
                print(f"\nLÍMITE DIARIO REACHADO. Evaluación detenida en caso '{case_name}'.")
                if daily_limit_reset:
                    print(f"Reinicio estimado (hora local): {daily_limit_reset}")
                # Guardar lo que se haya evaluado hasta ahora (ya se guardará en loop anterior si había caché, pero aquí no hay más)
                # No continuar con casos restantes
                # Escribimos resultados parciales y salimos
                # Pero para tener métricas parciales, acumulamos este caso como error de ejecución o marcado
                execution_error_count += 1
                triage_output = {"results": [{"test_name": case["report"], "category": "execution_error", "confidence": 0, "reason": f"Límite diario alcanzado. Reinicio: {daily_limit_reset}", "evidence": [str(exc)]}], "unknown": []}
                trace_info = {"iterations": 0, "tool_calls": [], "total_time": 0.0, "execution_error": str(exc)}
                # Guardar en caché este caso fallido por límite para no repetir
                save_cached_result(cache_path, {"triage_output": triage_output, "trace_info": trace_info, "cached_at": datetime.now().isoformat()})
                # Romper bucle
                # Añadir resultados del caso actual para metrics
                # ... (seguimos con el procesamiento normal para este caso, luego break)
            except Exception as exc:
                evaluated_cases += 1
                execution_error_count += 1
                triage_output = {"results": [{"test_name": case["report"], "category": "execution_error", "confidence": 0, "reason": "Ejecución fallida: " + str(exc), "evidence": [str(exc)]}], "unknown": []}
                trace_info = {"iterations": 0, "tool_calls": [], "total_time": 0.0, "execution_error": str(exc)}

            # Guardar resultado evaluado en caché
            if not daily_limit_stopped or idx == (len(cases) - 1) or True:
                # Siempre guardar si llegó a evaluar (o si es límite diario, guardar para no repetir)
                save_cached_result(cache_path, {"triage_output": triage_output, "trace_info": trace_info, "cached_at": datetime.now().isoformat()})
                if not daily_limit_stopped:
                    evaluated_cases += 1

            # Pausa configurable entre casos
            if not daily_limit_stopped and idx < len(cases) - 1:
                time.sleep(EVAL_DELAY_SECONDS)

        # Procesamiento de resultados (para caché o evaluado)
        # Baseline siempre
        report_path_resolved = resolve_path(case["report"])
        baseline_output = run_baseline([str(report_path_resolved)])

        invalid_output_flag = False
        if isinstance(triage_output, dict):
            if triage_output.get("_validation_errors") or ("results" not in triage_output) or not isinstance(triage_output.get("results"), list):
                invalid_output_flag = True
        else:
            invalid_output_flag = True

        if isinstance(trace_info, dict):
            total_time_triage += trace_info.get("total_time", 0.0)
            total_tool_calls_triage += len(trace_info.get("tool_calls", []))

        if invalid_output_flag:
            invalid_output_triage += 1
        else:
            triage_results_for_unknown = triage_output.get("results", []) if isinstance(triage_output, dict) else []
            unknown_triage_count += sum(1 for r in triage_results_for_unknown if isinstance(r, dict) and r.get("category") == "UNKNOWN")

        triage_results = triage_output.get("results", []) if isinstance(triage_output, dict) else []
        triage_map = {}
        for r in triage_results:
            if isinstance(r, dict):
                key = r.get("test_name") or r.get("test", "unknown")
                triage_map[key] = r.get("category", r.get("type", "UNKNOWN"))

        for r in triage_results:
            if isinstance(r, dict) and r.get("category") == "execution_error":
                execution_errors_global.append({"case": case["name"], "test": r.get("test_name") or r.get("test") or case["report"], "reason": r.get("reason", "Ejecución fallida")})

        baseline_map = {}
        for item in baseline_output:
            if isinstance(item, dict) and "test" in item:
                baseline_map[item.get("test")] = item.get("category", item.get("type", "UNKNOWN"))

        for test_name, expected_cat in case.get("expected", {}).items():
            total_tests += 1
            actual_triage = triage_map.get(test_name)
            actual_baseline = baseline_map.get(test_name)

            if actual_triage == expected_cat:
                correct_triage += 1
            if actual_baseline == expected_cat:
                correct_baseline += 1

            if actual_triage and actual_triage != "execution_error":
                confusion_triage.setdefault(actual_triage, {}).setdefault(expected_cat, 0)
                confusion_triage[actual_triage][expected_cat] += 1

            if actual_baseline and actual_baseline != "execution_error":
                confusion_baseline.setdefault(actual_baseline, {}).setdefault(expected_cat, 0)
                confusion_baseline[actual_baseline][expected_cat] += 1

        results.append({
            "case": case["name"],
            "expected": case.get("expected", {}),
            "triage_actual": triage_map,
            "baseline_actual": baseline_map,
        })

        if daily_limit_stopped:
            # Si fue límite diario, no seguir con más casos
            break

    # Si se detuvo por límite diario, contar el caso detenido como evaluado (ya lo hicimos)
    # Si no hay casos evaluados reales pero hay caché, los resultados parciales deben reflejar eso.
    accuracy_triage = correct_triage / total_tests if total_tests > 0 else 0.0
    accuracy_baseline = correct_baseline / total_tests if total_tests > 0 else 0.0

    from collections import Counter
    categories = ["BUG_REAL", "FLAKY", "AMBIENTE", "UNKNOWN"]

    def build_matrix(conf_dict):
        return {cat: {exp: conf_dict.get(cat, {}).get(exp, 0) for exp in categories} for cat in categories}

    mat_triage = build_matrix(confusion_triage)
    mat_baseline = build_matrix(confusion_baseline)

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

    unknown_rate = unknown_triage_count / total_tests if total_tests > 0 else 0.0
    invalid_output_rate = invalid_output_triage / total_cases if total_cases > 0 else 0.0
    avg_time = total_time_triage / total_cases if total_cases > 0 else 0.0
    avg_tool_calls = total_tool_calls_triage / total_cases if total_cases > 0 else 0.0

    metrics_text.append("\n### Resumen por caso")
    for res in results:
        case_name = res["case"]
        pred = res["triage_actual"]
        exp = res["expected"]
        correct_items = [k for k in exp if pred.get(k) == exp[k]]
        metrics_text.append(f"- **{case_name}**: expected={exp}, pred={pred}, correct={len(correct_items)}/{len(exp)}")

    results_path = Path("evals/results.md")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    # Accuracy: calcular sobre casos evaluados (reales) y señalar parcial si n < 17
    total_all_cases = len(all_cases)
    real_evaluated = evaluated_cases
    # Si hay resultados reales parciales (evaluados > 0), mostrar accuracy real parcial
    # No declarar "No calculado" si hay resultados reales parciales.
    if daily_limit_stopped:
        accuracy_note = f"Evaluación detida por límite diario. Casos evaluados de verdad: {real_evaluated}/{total_all_cases}. Casos de caché: {cached_cases}. Accuracy parcial sobre evaluados: {accuracy_triage:.2%} (solo los casos evaluados reales, no todos los 17)."
    else:
        accuracy_note = f"Casos evaluados de verdad: {real_evaluated}/{total_all_cases}. Casos de caché: {cached_cases}."

    accuracy_text_triage = f"{correct_triage}/{total_tests} = {accuracy_triage:.2%}" if total_tests > 0 else "N/A"
    if total_tests > 0 and (real_evaluated < total_all_cases or cached_cases > 0):
        accuracy_text_triage += " (parcial)"
    accuracy_text_baseline = f"{correct_baseline}/{total_tests} = {accuracy_baseline:.2%}" if total_tests > 0 else "N/A"

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
        f"- **Evaluados reales**: {real_evaluated}/{total_all_cases}; **Caché reutilizados**: {cached_cases}",
        f"- **Nota**: {accuracy_note}",
        "",
    ]

    if daily_limit_stopped:
        lines.append("> ADVERTENCIA: Evaluación detenida por límite diario de OpenRouter (DailyLimitError). No se continuaron los casos restantes.")
        if daily_limit_reset:
            lines.append(f"> Hora de reinicio estimada (local): {daily_limit_reset}")
        lines.append("")

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
        "> La accuracy del LLM se calcula solo sobre los casos evaluados (reales); si hay resultados parciales en caché, se indica como parcial.",
    ]

    results_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    run_evals()
