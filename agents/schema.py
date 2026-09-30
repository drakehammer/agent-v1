"""Schema estructurado para la respuesta del agente de triage."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional


class ResultItem(BaseModel):
    test_name: str = Field(..., min_length=1, description="Identificador del test fallido.")
    category: str = Field(
        ...,
        pattern=r"^(BUG_REAL|FLAKY|AMBIENTE|UNKNOWN)$",
        description="Categoría asignada.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza de la clasificación (0-1).")
    reason: str = Field(..., min_length=1, description="Explicación breve del razonamiento.")
    evidence: List[str] = Field(
        ...,
        description="Evidencia que respalda la categoría. Obligatorio y no vacío salvo que se justifique UNKNOWN.",
    )

    @model_validator(mode="after")
    def check_evidence(self) -> "ResultItem":
        if self.category == "UNKNOWN":
            if not self.evidence:
                if self.reason and any(word in self.reason.lower() for word in ["evidencia", "insuficiente", "falta", "no hay", "sin evidencia"]):
                    pass
                else:
                    raise ValueError("UNKNOWN debe justificar la falta de evidencia en reason.")
        else:
            if not self.evidence or any(str(e).strip() == "" for e in self.evidence):
                raise ValueError("Evidencia obligatoria no vacía para categoría no-UNKNOWN.")
        return self

    @field_validator("evidence")
    @classmethod
    def evidence_not_empty_for_non_unknown(cls, v: List[str], info) -> List[str]:
        # En Pydantic v2, para acceder a category necesitamos el contexto; lo manejamos a nivel de modelo
        return v


class UnknownItem(BaseModel):
    test: str = Field(..., min_length=1, description="Identificador del test.")
    reason: str = Field(..., min_length=1, description="Por qué no hay evidencia suficiente.")
    evidence: Optional[List[str]] = Field(default_factory=list, description="Evidencia parcial si existe.")


class TriageOutput(BaseModel):
    results: List[ResultItem] = Field(default_factory=list)
    unknown: List[UnknownItem] = Field(default_factory=list)
    summary: Optional[str] = Field(default="", description="Resumen ejecutivo del diagnóstico.")
    model_used: Optional[str] = Field(default="", description="Modelo usado para la clasificación.")

    @model_validator(mode="after")
    def check_no_duplicates_and_evidence(self) -> "TriageOutput":
        # No duplicados en results
        names = [r.test_name for r in self.results]
        if len(names) != len(set(names)):
            duplicates = {name for name in names if names.count(name) > 1}
            raise ValueError(f"Tests duplicados en results: {duplicates}")

        # Exactamente un resultado por test analizado: como no tenemos la lista de tests analizados
        # en el schema, esta regla se aplica en el agente (verificación contra los fallos del reporte).

        # Evidence no vacío salvo UNKNOWN justificado
        for r in self.results:
            if r.category == "UNKNOWN":
                # Justificación debe estar en reason y evidence puede ser vacío o contener explicación
                if not r.evidence:
                    # Permitido si reason explica por qué no hay evidencia
                    if "evidencia" not in r.reason.lower() and "sin evidencia" not in r.reason.lower() and "insuficiente" not in r.reason.lower():
                        raise ValueError(
                            f"UNKNOWN para {r.test_name} debe justificar en 'reason' la falta de evidencia."
                        )
            else:
                if not r.evidence or any(str(e).strip() == "" for e in r.evidence):
                    raise ValueError(
                        f"Evidencia no debe ser vacía para categoría {r.category} en {r.test_name}."
                    )
        return self
