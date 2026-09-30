#!/usr/bin/env python3
"""Agente de triage con ciclo manual de tool calling (OpenRouter + openai SDK)."""

import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

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
                "Eres un agente de triage de fallos de tests automatizados. Tu tarea es clasificar cada test fallido en BUG_REAL, FLAKY o AMBIENTE. "
                "Usa evidencia del reporte JUnit XML. Si la evidencia no alcanza, usa UNKNOWN en lugar de inventar. "
                "Genera un JSON final con 'results' (lista de objetos) y opcionalmente 'unknown' (lista)."
            ),
        },
        {"role": "user", "content": f"Analiza el reporte de tests: {str(full_report_path)}"},
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
            args_raw = tc.function.arguments
            args_dict = json.loads(args_raw) if args_raw else {}

            tool_entry = {
                "tool": tool_name,
                "arguments": args_dict,
                "result": None,
                "error": None,
            }

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
                    result = {"error": f"Herramienta desconocida: {tool_name}"}

                tool_entry["result"] = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            except Exception as exc:
                tool_entry["error"] = str(exc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                })

            trace["tool_calls"].append(tool_entry)

    else:
        # Se alcanzó el límite de iteraciones sin respuesta final
        trace["output"] = json.dumps({
            "results": [{"test": "unknown", "category": "UNKNOWN", "confidence": 0.0,
                         "reason": "Límite de iteraciones alcanzado sin respuesta final", "evidence": ""}],
            "unknown": [{"test": "unknown", "reason": "Sin evidencia suficiente"}],
        }, ensure_ascii=False)

    trace["total_time"] = time.time() - start_time

    # Guardar traza
    traces_dir = Path("traces")
    traces_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = traces_dir / f"{timestamp}.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)

    # Intentar parsear la salida del modelo como JSON
    raw_output = trace.get("output") or "{}"
    # Si no es JSON válido, intentar extraer JSON de la cadena
    parsed_output: dict = {}
    try:
        parsed_output = json.loads(raw_output)
    except json.JSONDecodeError:
        # Intentar extraer bloque JSON de la respuesta
        import re
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            try:
                parsed_output = json.loads(match.group(0))
            except Exception:
                pass
        # Si aún no se puede, devolver estructura mínima
        if not parsed_output:
            parsed_output = {
                "results": [{"test": str(report_path_str), "category": "UNKNOWN",
                             "confidence": 0.0, "reason": "Respuesta del modelo no es JSON válido",
                             "evidence": raw_output[:200]}],
                "unknown": [{"test": str(report_path_str), "reason": "Respuesta no parseable"}],
            }

    # Asegurar campos mínimos
    if "results" not in parsed_output:
        parsed_output["results"] = []
    if "unknown" not in parsed_output:
        parsed_output["unknown"] = []

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
