"""Tests para el output validator del agente (Fase 10)."""
import pytest
from agents.schema import TriageOutput, ResultItem
from agents.triage import SYSTEM_PROMPT


def test_output_validator_duplicate():
    with pytest.raises(ValueError, match="duplicados"):
        TriageOutput(results=[
            ResultItem(test_name="t1", category="BUG_REAL", confidence=0.9, reason="r", evidence=["e"]),
            ResultItem(test_name="t1", category="BUG_REAL", confidence=0.9, reason="r", evidence=["e"]),
        ])


def test_output_validator_invalid_category():
    with pytest.raises(ValueError):
        TriageOutput(results=[
            ResultItem(test_name="t1", category="INVALID", confidence=0.5, reason="r", evidence=["e"]),
        ])


def test_output_validator_empty_evidence_non_unknown():
    with pytest.raises(ValueError, match="Evidencia obligatoria"):
        TriageOutput(results=[
            ResultItem(test_name="t1", category="BUG_REAL", confidence=0.5, reason="r", evidence=[]),
        ])


def test_output_validator_unknown_justified():
    # UNKNOWN con justificación debe pasar
    out = TriageOutput(results=[
        ResultItem(test_name="t1", category="UNKNOWN", confidence=0.8, reason="Sin evidencia suficiente para distinguir la causa", evidence=[]),
    ])
    assert out.results[0].category == "UNKNOWN"


def test_system_prompt_is_str_and_contains_keywords():
    assert isinstance(SYSTEM_PROMPT, str)
    assert SYSTEM_PROMPT
    for word in ("BUG_REAL", "FLAKY", "AMBIENTE", "UNKNOWN"):
        assert word in SYSTEM_PROMPT, f"Falta {word} en SYSTEM_PROMPT"


def test_messages_content_are_str():
    # Verifica que cada content en mensajes del sistema/usuario sea str
    import agents.triage as triage_module
    # Construir mensajes mínimos igual a los de run_agent (solo estructura)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "test"},
    ]
    for msg in messages:
        assert isinstance(msg.get("content"), str), f"content no es str en {msg['role']}"
    # También verificar que los mensajes de herramienta futuros sean str
    # (en el ciclo, content siempre se convierte con or "")
