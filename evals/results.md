# Resultados de Evaluación
Modelo usado: `openrouter/free`
Fecha: 2026-09-30 11:04:22

## Comparación Triage vs Baseline (18 tests)
- **Triage (LLM)**: No calculado (evaluación no real: tool_calls == 0 o time == 0)
- **Baseline (reglas)**: No calculado
- **Unknown rate (Triage)**: 0.00%
- **Invalid-output rate (Triage)**: 0.00%
- **Average tool calls (Triage)**: 0.0
- **Average execution time (Triage)**: 0.00s

> WARNING: Evaluacion no considerada real: no se registraron llamadas a herramientas (tool_calls == 0) o tiempo == 0.

## Errores de ejecución
| Caso | Test | Razón |
|------|------|-------|
| bug_real_assertion | synthetic/bug_real_assertion.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| bug_real_wrong_value | synthetic/bug_real_wrong_value.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| bug_real_status_code | synthetic/bug_real_status_code.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| bug_real_field_null | synthetic/bug_real_field_null.xml | Ejecución fallida: No se encontró el reporte: synthetic/bug_real_field_null.xml |
| flaky_timeout | synthetic/flaky_timeout.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| flaky_race_condition | synthetic/flaky_race_condition.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| flaky_order_dependent | synthetic/flaky_order_dependent.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| flaky_intermittent | synthetic/flaky_intermittent.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiente_connection_refused | synthetic/ambiente_connection_refused.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiente_dns | synthetic/ambiente_dns.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiente_credentials | synthetic/ambiente_credentials.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiente_service_down | synthetic/ambiente_service_down.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiguous_assertion | synthetic/ambiguous_assertion.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiguous_timeout | synthetic/ambiguous_timeout.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| ambiguous_http_error | synthetic/ambiguous_http_error.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| multiple_failures | synthetic/multiple_failures.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |
| missing_context | synthetic/missing_context.xml | Ejecución fallida: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}} |

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
- **bug_real_assertion**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_assertion.xml': 'execution_error'}, correct=0/1
- **bug_real_wrong_value**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_wrong_value.xml': 'execution_error'}, correct=0/1
- **bug_real_status_code**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_status_code.xml': 'execution_error'}, correct=0/1
- **bug_real_field_null**: expected={'ApiTest.testGetUser': 'BUG_REAL'}, pred={'synthetic/bug_real_field_null.xml': 'execution_error'}, correct=0/1
- **flaky_timeout**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_timeout.xml': 'execution_error'}, correct=0/1
- **flaky_race_condition**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_race_condition.xml': 'execution_error'}, correct=0/1
- **flaky_order_dependent**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_order_dependent.xml': 'execution_error'}, correct=0/1
- **flaky_intermittent**: expected={'ApiTest.testGetUser': 'FLAKY'}, pred={'synthetic/flaky_intermittent.xml': 'execution_error'}, correct=0/1
- **ambiente_connection_refused**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_connection_refused.xml': 'execution_error'}, correct=0/1
- **ambiente_dns**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_dns.xml': 'execution_error'}, correct=0/1
- **ambiente_credentials**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_credentials.xml': 'execution_error'}, correct=0/1
- **ambiente_service_down**: expected={'ApiTest.testGetUser': 'AMBIENTE'}, pred={'synthetic/ambiente_service_down.xml': 'execution_error'}, correct=0/1
- **ambiguous_assertion**: expected={'AmbiguousTest.testAmbiguous': 'UNKNOWN'}, pred={'synthetic/ambiguous_assertion.xml': 'execution_error'}, correct=0/1
- **ambiguous_timeout**: expected={'AmbiguousTimeout.testTimeout': 'UNKNOWN'}, pred={'synthetic/ambiguous_timeout.xml': 'execution_error'}, correct=0/1
- **ambiguous_http_error**: expected={'AmbiguousHttp.testHttp': 'UNKNOWN'}, pred={'synthetic/ambiguous_http_error.xml': 'execution_error'}, correct=0/1
- **multiple_failures**: expected={'MultiFailure.testA': 'BUG_REAL', 'MultiFailure.testB': 'AMBIENTE'}, pred={'synthetic/multiple_failures.xml': 'execution_error'}, correct=0/2
- **missing_context**: expected={'MissingContext.testMissing': 'UNKNOWN'}, pred={'synthetic/missing_context.xml': 'execution_error'}, correct=0/1

> Nota: los resultados son reales tras ejecutar `run_evals.py`. No se inventan cifras.