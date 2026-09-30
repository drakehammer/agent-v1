#!/usr/bin/env python3
"""Agente de triage con ciclo manual de tool calling (OpenRouter + openai SDK)."""

import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from agents.schema import TriageOutput, ResultItem
from tools import TOOL_SCHEMAS
from tools.read_report import read_report
from tools.read_test import read_test
from tools.write_summary import write_summary

MAX_ITERATIONS = 10
MAX_RETRIES = 3


def call_api_with_retry(client: OpenAI, model: str, messages: list, tools: list) -> dict:
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            return response
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    raise last_exc


def resolve_report_path(path_arg: str) -> Path:
    """Resuelve rutas de reporte con soporte para múltiples formatos."""
    # Intentar con path absoluto o relativo directo
    p = Path(path_arg)
    if p.exists():
        return p.resolve()
    # Intentar con data/samples/synthetic/
    synthetic_dir = Path("data/samples/synthetic")
    synthetic_path = synthetic_dir / Path(path_arg)
    if synthetic_path.exists():
        return synthetic_path.resolve()
    synthetic_path2 = synthetic_dir / p.name
    if synthetic_path2.exists():
        return synthetic_path2.resolve()
    # Intentar con data/samples/real/
    real_dir = Path("data/samples/real")
    real_path = real_dir / Path(path_arg)
    if real_path.exists():
        return real_path.resolve()
    # Intentar con nombre solo
    if synthetic_dir.exists() and (synthetic_dir / p.name).exists():
        return (synthetic_dir / p.name).resolve()
    raise FileNotFoundError(f"No se encontró el reporte: {path_arg}")


def run_agent(report_path_str: str) -> tuple[dict, dict]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("AGENT_MODEL", "openrouter/free")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY no está configurada en variables de entorno.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    # Resolver ruta del reporte
    full_report_path = resolve_report_path(report_path_str)

    messages = [
        {
            "role": "system",
            "content": (
                "Estrategia explícita (seguir en orden): 1. Inspect the report. 2. Identify failed tests. 3. Gather relevant evidence. 4. Inspect test source when useful. 5. Distinguish facts from hypotheses. 6. Do not infer flaky behavior without evidence. 7. Do not infer environment failures from HTTP codes alone. 8. Prefer UNKNOWN when evidence is insufficient. 9. Provide evidence for every diagnosis. 10. Return only the required structured output. "
                "Política de confianza: la confianza representa la confianza en la evidencia disponible, no en una suposición. Un UNKNOWN de alta confianza es válido cuando la evidencia muestra claramente que los datos disponibles son insuficientes para determinar la causa raíz. "
                "Clasifica BUG_REAL solo con evidencia razonable. FLAKY solo con indicadores concretos (timeout/intermitencia, orden, referencias temporales, comportamiento no determinista, histórico, resultados distintos, race). AMBIENTE solo con indicadores de infraestructura (DNS, conexión, auth, servicio, 5xx REALMENTE de infra). No convertir 401/503 automáticamente en AMBIENTE. UNKNOWN es válido cuando hay varias explicaciones plausibles o falta contexto.",
                "No confundir patrones con evidencia (ej: 'expected true but was false' no define categoría por sí solo). Confianza refleja confianza en la evidencia disponible, no en una suposición. Un UNKNOWN de alta confianza es válido si los datos son claramente insuficientes."
                "Genera una respuesta final estructurada como JSON con 'results' (lista de objetos con test, category, confidence, reason, evidence) y 'unknown' (lista de objetos con test, reason, evidence opcional). "
                "Incluye un campo 'summary' breve sobre el diagnóstico general. No uses regex ni texto libre fuera del JSON estructurado."
            ),
        },
        {"role": "user", "content": f"Analiza el reporte: {str(full_report_path)}. Recopila evidencia. Separa Evidence (hechos del reporte) de Reasoning (razonamiento paso a paso). Devuelve JSON con results (test_name, category, confidence, reason, evidence) y unknown (test, reason, evidence) según corresponda."},
    ]

    trace: dict = {
        "input": str(report_path_str),
        "resolved_path": str(full_report_path),
        "model": model,
        "messages": [],
        "tool_calls": [],
        "iterations": 0,
        "total_time": 0.0,
        "output": None,
    }

    # Resolver fallos del reporte para validación de cantidad exacta y fallback
    expected_test_names = set()
    try:
        failed_report = read_report(str(report_path_str))
        expected_test_names = {f.get("test") for f in failed_report if f.get("test")}
    except Exception:
        pass

    start_time = time.time()

    for iteration in range(MAX_ITERATIONS):
        trace["iterations"] += 1
        response = call_api_with_retry(client, model, messages, TOOL_SCHEMAS)
        msg = response.choices[0].message

        trace["messages"].append({
            "role": "assistant",
            "content": msg.content or "",
        })

        # Si no hay llamadas a herramientas, asumimos que el modelo terminó
        if not msg.tool_calls:
            trace["output"] = msg.content
            break

        # Procesar cada llamada a herramienta
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            args_raw = tc.function.arguments or "{}"

            # --- Robustez: argumentos del modelo ---
            args_dict: dict = {}
            args_parse_error = None
            try:
                if isinstance(args_raw, str) and args_raw.strip() == "":
                    args_dict = {}
                elif isinstance(args_raw, str):
                    parsed = json.loads(args_raw)
                    args_dict = parsed if isinstance(parsed, dict) else {}
                    if not isinstance(parsed, dict):
                        args_parse_error = f"Argumentos no son objeto JSON (tipo: {type(parsed).__name__})"
                else:
                    args_dict = args_raw if isinstance(args_raw, dict) else {}
                    if not isinstance(args_raw, dict):
                        args_parse_error = f"Argumentos inesperados (tipo: {type(args_raw).__name__})"
            except Exception as exc:
                args_parse_error = f"JSON inválido en argumentos: {exc}"
                args_dict = {}

            tool_entry = {
                "tool": tool_name,
                "arguments_raw": args_raw,
                "arguments": args_dict,
                "result": None,
                "error": args_parse_error,
            }

            # Si hay error de parseo, devolver observación al modelo sin llamar la herramienta
            if args_parse_error:
                tool_entry["error"] = args_parse_error
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": args_parse_error, "suggestion": "Corrige los argumentos JSON para esta llamada."}, ensure_ascii=False),
                })
                trace["tool_calls"].append(tool_entry)
                continue

            # Validación de argumentos requeridos básicos
            missing_args = []
            if tool_name == "read_report" and (not args_dict.get("path") or not isinstance(args_dict.get("path"), str)):
                missing_args.append("path (string) requerido")
            elif tool_name == "read_test" and (not args_dict.get("path") or not isinstance(args_dict.get("path"), str)):
                missing_args.append("path (string) requerido")
            elif tool_name == "write_summary":
                if not args_dict.get("path") or not isinstance(args_dict.get("path"), str):
                    missing_args.append("path (string) requerido")
                if not args_dict.get("content") or not isinstance(args_dict.get("content"), str):
                    missing_args.append("content (string) requerido")

            if missing_args and tool_name in ("read_report", "read_test", "write_summary"):
                msg_missing = f"Faltan argumentos: {', '.join(missing_args)}. Proporciona valores válidos."
                tool_entry["error"] = msg_missing
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": msg_missing}, ensure_ascii=False),
                })
                trace["tool_calls"].append(tool_entry)
                continue

            try:
                if tool_name == "read_report":
                    result = read_report(args_dict.get("path", ""))
                elif tool_name == "read_test":
                    result = read_test(args_dict.get("path", ""))
                elif tool_name == "write_summary":
                    result = write_summary(
                        args_dict.get("path", ""),
                        args_dict.get("content", ""),
                    )
                else:
                    result = {"error": f"Herramienta desconocida: {tool_name}", "suggestion": "Usa read_report, read_test o write_summary."}

                tool_entry["result"] = result
                if isinstance(result, dict) and result.get("error"):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"error": result["error"], "info": "El tool devolvió un error controlado."}, ensure_ascii=False),
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            except Exception as exc:
                error_str = f"Excepción en herramienta '{tool_name}': {exc}"
                tool_entry["error"] = error_str
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": error_str, "suggestion": "Corrige la llamada o usa argumentos válidos."}, ensure_ascii=False),
                })

            trace["tool_calls"].append(tool_entry)

    else:
        # Se alcanzó el límite de iteraciones sin respuesta final
        # Devolver un resultado válido para cada test analizado (F4: no ocultar con un solo item)
        fallback_results = []
        for tn in expected_test_names:
            fallback_results.append({
                "test_name": tn,
                "category": "UNKNOWN",
                "confidence": 0.0,
                "reason": "Límite de iteraciones alcanzado; sin evidencia suficiente para distinguir la causa raíz.",
                "evidence": [],
            })
        trace["output"] = json.dumps({
            "results": fallback_results if fallback_results else [{"test_name": "unknown", "category": "UNKNOWN", "confidence": 0.0, "reason": "Límite de iteraciones alcanzado.", "evidence": []}],
        }, ensure_ascii=False)

    trace["total_time"] = time.time() - start_time

    # Guardar traza
    traces_dir = Path("traces")
    traces_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = traces_dir / f"{timestamp}.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)

    # --- Validación estructurada del output final (sin regex genérica) ---
    raw_output = trace.get("output") or "{}"
    parsed_output: dict = {}
    validation_errors = []

    # Intento 1: parseo directo como JSON
    try:
        parsed_raw = json.loads(raw_output)
        if isinstance(parsed_raw, dict):
            parsed_output = parsed_raw
        else:
            validation_errors.append(f"Root JSON es {type(parsed_raw).__name__}, no dict")
    except Exception as exc:
        validation_errors.append(f"JSON directo falló: {exc}")

    # Intento 2: extraer bloque de código o JSON embebido
    if not parsed_output or validation_errors:
        try:
            import re
            candidates = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw_output, re.DOTALL)
            best = None
            for c in candidates:
                if "results" in c or "category" in c:
                    best = c
                    break
            if best is None and candidates:
                best = max(candidates, key=len)
            if best:
                try:
                    parsed_output = json.loads(best)
                    if not isinstance(parsed_output, dict):
                        validation_errors.append("JSON extraído no es dict")
                        parsed_output = {}
                except Exception as exc:
                    validation_errors.append(f"JSON extraído falló: {exc}")
        except Exception:
            pass

    # Intento 3: validación con Pydantic (si hay datos mínimos)
    if not parsed_output:
        parsed_output = {}

    # Asegurar estructura mínima si viene vacío o incompleto
    if not isinstance(parsed_output, dict):
        parsed_output = {}
    if "results" not in parsed_output:
        parsed_output["results"] = []

    # Normalización de resultados según schema exacto
    try:
        results_raw = parsed_output.get("results", [])
        if isinstance(results_raw, list):
            normalized_results = []
            for item in results_raw:
                if isinstance(item, dict):
                    test_name = item.get("test_name") or item.get("test", "unknown")
                    evidence_raw = item.get("evidence", [])
                    if isinstance(evidence_raw, str):
                        evidence_list = [evidence_raw] if evidence_raw.strip() else []
                    elif isinstance(evidence_raw, list):
                        evidence_list = [str(e) for e in evidence_raw if str(e).strip() != ""]
                    else:
                        evidence_list = [str(evidence_raw)]
                    category = item.get("category", "UNKNOWN")
                    confidence = item.get("confidence", 0.0)
                    if not isinstance(confidence, (int, float)):
                        confidence = 0.0
                    confidence = float(confidence)
                    confidence = max(0.0, min(1.0, confidence))
                    reason = item.get("reason", "")
                    if not isinstance(reason, str) or not reason.strip():
                        reason = "Sin razón explícita"
                    normalized_results.append({
                        "test_name": str(test_name) if test_name else "unknown",
                        "category": str(category).upper() if isinstance(category, str) else "UNKNOWN",
                        "confidence": confidence,
                        "reason": reason,
                        "evidence": evidence_list,
                    })
                else:
                    normalized_results.append({"test_name": "unknown", "category": "UNKNOWN", "confidence": 0.0, "reason": "Item malformado", "evidence": [str(item)]})
            parsed_output["results"] = normalized_results
        else:
            parsed_output["results"] = [{"test_name": "unknown", "category": "UNKNOWN", "confidence": 0.0, "reason": "results no es lista", "evidence": [str(results_raw)]}]

        # Validar duplicados
        result_names = [r.get("test_name") for r in parsed_output.get("results", [])]
        if len(result_names) != len(set(result_names)):
            duplicates = {n for n in result_names if result_names.count(n) > 1}
            validation_errors.append(f"Resultados duplicados: {duplicates}")

        # Validar cantidad exacta por test analizado
        if expected_test_names:
            result_names_set = set(result_names)
            missing = expected_test_names - result_names_set
            extra = result_names_set - expected_test_names
            if missing:
                validation_errors.append(f"Faltan resultados para tests: {missing}")
            if extra:
                validation_errors.append(f"Resultados extra para tests no fallidos: {extra}")
            if not missing and not extra and len(result_names) != len(expected_test_names):
                validation_errors.append(f"Cantidad de resultados ({len(result_names)}) no coincide con fallos ({len(expected_test_names)})")

        # Validación de evidencia obligatoria y justificación UNKNOWN
        for r in parsed_output.get("results", []):
            cat = r.get("category", "UNKNOWN")
            ev = r.get("evidence", [])
            reason_text = r.get("reason", "")
            if cat == "UNKNOWN":
                if not reason_text or not any(word in reason_text.lower() for word in ["evidencia", "evidencia insuficiente", "sin evidencia", "no hay suficiente", "falta de evidencia"]):
                    validation_errors.append(f"UNKNOWN para {r.get('test_name')} debe explicar en 'reason' la falta de evidencia.")
            else:
                if not ev or not all(isinstance(e, str) and e.strip() for e in ev):
                    validation_errors.append(f"Evidencia obligatoria no vacía para {r.get('test_name')} (categoria {cat}).")

        # Simplificar schema: eliminar estructura duplicada unknown
        parsed_output.pop("unknown", None)

        try:
            model_name = model if 'model' in locals() else os.environ.get("AGENT_MODEL", "unknown")
            triage_model = TriageOutput(
                results=parsed_output.get("results", []),
                summary=parsed_output.get("summary", ""),
                model_used=parsed_output.get("model_used", model_name),
            )
            parsed_output = triage_model.model_dump()
        except Exception as pydantic_exc:
            parsed_output["_validation_errors"] = validation_errors + [f"Pydantic: {pydantic_exc}"]
    except Exception as exc:
        parsed_output["_validation_errors"] = validation_errors + [f"Normalización: {exc}"]

    # Si aún no hay resultados y hay errores de validación, usar estructura mínima
    if not parsed_output.get("results") and (validation_errors or parsed_output.get("_validation_errors")):
        parsed_output["results"] = [{
            "test_name": str(report_path_str),
            "category": "UNKNOWN",
            "confidence": 0.0,
            "reason": "Respuesta del modelo no es JSON válido o no pasó validación estructurada.",
            "evidence": [raw_output[:300]],
        }]
        parsed_output["unknown"] = [{"test": str(report_path_str), "reason": "Sin evidencia suficiente tras validación.", "evidence": [""]}]

    # Incluir metadatos de validación para depuración sin romper el contrato
    if validation_errors and "_validation_errors" not in parsed_output:
        parsed_output["_validation_errors"] = validation_errors

    return parsed_output, trace


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m agents.triage data/samples/<reporte>.xml")
        sys.exit(1)
    report_arg = sys.argv[1]
    result, trace = run_agent(report_arg)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
