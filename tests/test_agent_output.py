"""Tests para el output validator del agente (Fase 10)."""
import pytest
from agents.schema import TriageOutput, ResultItem, UnknownItem


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
