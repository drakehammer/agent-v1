# Resultados de Evaluación
Modelo usado: `openrouter/free`
Fecha: 2026-09-30 10:56:49

## Comparación Triage vs Baseline (18 tests)
- **Triage (LLM)**: 0/18 = 0.00%
- **Baseline (reglas)**: 0/18 = 0.00%
- **Unknown rate (Triage)**: 0.00%
- **Invalid-output rate (Triage)**: 0.00%
- **Average tool calls (Triage)**: 0.0
- **Average execution time (Triage)**: 0.00s

## Matriz de confusión (Triage)
```
Predicted \ Expected  BUG_REAL  FLAKY  AMBIENTE  UNKNOWN
BUG_REAL     0     0     0     0
FLAKY     0     0     0     0
AMBIENTE     0     0     0     0
UNKNOWN     0     0     0     0
```

## Métricas por categoría (Triage)

### Métricas por categoría (Triage)
| Cat | Precision | Recall | F1 |
|-----|-----------|--------|----|
| BUG_REAL | 0.00% | 0.00% | 0.00% |
| FLAKY | 0.00% | 0.00% | 0.00% |
| AMBIENTE | 0.00% | 0.00% | 0.00% |
| UNKNOWN | 0.00% | 0.00% | 0.00% |

### Resumen por caso
- **bug_real_assertion**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_assertion.xml': 'ERROR'}, correct=0/1
- **bug_real_wrong_value**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_wrong_value.xml': 'ERROR'}, correct=0/1
- **bug_real_status_code**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_status_code.xml': 'ERROR'}, correct=0/1
- **bug_real_field_null**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_field_null.xml': 'ERROR'}, correct=0/1
- **flaky_timeout**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_timeout.xml': 'ERROR'}, correct=0/1
- **flaky_race_condition**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_race_condition.xml': 'ERROR'}, correct=0/1
- **flaky_order_dependent**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_order_dependent.xml': 'ERROR'}, correct=0/1
- **flaky_intermittent**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_intermittent.xml': 'ERROR'}, correct=0/1
- **ambiente_connection_refused**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_connection_refused.xml': 'ERROR'}, correct=0/1
- **ambiente_dns**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_dns.xml': 'ERROR'}, correct=0/1
- **ambiente_credentials**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_credentials.xml': 'ERROR'}, correct=0/1
- **ambiente_service_down**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_service_down.xml': 'ERROR'}, correct=0/1
- **ambiguous_assertion**: expected={'AmbiguousTest.testAmbiguous': 'UNKNOWN'}, pred={'synthetic/ambiguous_assertion.xml': 'ERROR'}, correct=0/1
- **ambiguous_timeout**: expected={'AmbiguousTimeout.testTimeout': 'UNKNOWN'}, pred={'synthetic/ambiguous_timeout.xml': 'ERROR'}, correct=0/1
- **ambiguous_http_error**: expected={'AmbiguousHttp.testHttp': 'UNKNOWN'}, pred={'synthetic/ambiguous_http_error.xml': 'ERROR'}, correct=0/1
- **multiple_failures**: expected={'MultiFailure.testA': 'BUG_REAL', 'MultiFailure.testB': 'AMBIENTE'}, pred={'synthetic/multiple_failures.xml': 'ERROR'}, correct=0/2
- **missing_context**: expected={'MissingContext.testMissing': 'UNKNOWN'}, pred={'synthetic/missing_context.xml': 'ERROR'}, correct=0/1

> Nota: los resultados son reales tras ejecutar `run_evals.py`. No se inventan cifras.