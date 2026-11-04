# Matriz de trazabilidad: BRD → regla → componente → prueba

Fuentes: BRD (necesidades BN-xx), User Stories US-xx (Gherkin), casos de uso CU-xx de la U3, y reglas del paquete (R-P*).
"✔" = implementado y probado · "—" = fuera de este incremento (ver ADR-005).

| Origen | Regla de negocio | Componente (código) | Prueba | Estado |
|---|---|---|---|---|
| R-P1 | Procesar sólo si actor activo ∧ detalle no vacío ∧ autorización | `reglas.PUEDE_PROCESARSE` (`ActorActivo`, `DetalleNoVacio`, `Autorizado`) | `test_dominio::test_puede_procesarse_requiere_las_tres_condiciones`, `test_casos_csv::test_120_casos_coinciden_con_el_oraculo` | ✔ |
| R-P2 | Beneficio si preferente ∧ total ≥ 1500 ∧ ¬promoción | `reglas.BENEFICIO_REFERENCIA` (`ActorPreferente`, `TotalMinimo`, `~PromocionActiva`) | `test_dominio::test_beneficio_referencia` (límite 1500 inclusivo) | ✔ |
| R-P3 | ≥3 Specifications con AND/OR/NOT | `domain/specifications.py` (11 hojas + And/Or/Not) | `test_dominio::test_operadores_and_or_not_son_composables` (De Morgan), `test_arquitectura::test_hay_al_menos_tres_specifications_hoja` | ✔ |
| R-P3 | Máquina de estados | `domain/state_machine.py`, `Pedido.validar/preparar/entregar/cancelar` | `test_dominio::TestMaquinaDeEstados` (matriz 5×4) , `test_casos_csv::test_20_transiciones…` | ✔ |
| R-P3 | Domain Events | `domain/events.py`, `Pedido.extraer_eventos`, `BusDeEventosEnMemoria` | `test_dominio::test_flujo_completo_emite_eventos…`, `test_servicios::test_flujo_completo_persiste…` | ✔ |
| R-P4 | Validar cantidades e importes | `Cantidad`, `Dinero`, `PedidoIn` (`gt=0`) | `test_dominio::TestValueObjects`, `test_api::test_400_cantidad_invalida` | ✔ |
| R-P4 | Disponibilidad / capacidad | `StockSuficiente`, `ProductosHabilitados`, `Producto.descontar` | `test_servicios::test_stock_insuficiente_impide_validar`, `…producto_deshabilitado…`, `test_dominio::test_preparar_sin_stock…` | ✔ |
| R-P4 | Transiciones inválidas | `TransicionInvalida` → 409 | `test_api::test_409_transicion_invalida`, `test_servicios::test_cancelar_y_transiciones_invalidas` | ✔ |
| R-P5 | Contrato 200/201/400/404/409/422 | `api/errores.py` (ADR-006) | `test_api.py` completo | ✔ |
| BN-01 / US-02, US-03 / CU-02 | Receta completa y vigente (≤30 días) para controlados | `RecetaVigente`, `VENTA_CONTROLADA_CON_RECETA` | `test_dominio::test_receta_vigente_30_dias`, `test_controlado_exige_receta…` | ✔ (parcial: valida vigencia y presencia; no captura paciente/médico/cédula) |
| BN-10 / US-04 / CU-02 | Controlados >10 pzas o >$3,000 requieren autorización del Responsable | `ExcedeLimiteControlado`, `LIMITE_CONTROLADO_AUTORIZADO` | `test_dominio::test_limite_controlado_10_piezas_o_3000` | ✔ |
| US-01 / CU-01 | Venta sin restricciones descuenta existencia | `Pedido.preparar` + `Producto.descontar` | `test_servicios::test_flujo_completo_persiste…` (stock 37→34), `test_api::test_flujo_completo_200` | ✔ (existencia por producto, no por lote) |
| BN-02 / US-07, US-08 / CU-04 | Bloquear caducados y lotes retirados en todas las sucursales | — (requiere agregado `Lote`) | — | — |
| BN-05 / US-09 | Alertas de caducidad 90/60/30 días | — | — | — |
| BN-03, BN-04 / US-12, US-13 / CU-05 | Punto de reorden, alerta y orden de compra | — (`PedidoEntregado` es el punto de enganche) | — | — |
| US-05, US-06 / CU-03 | Sustitución de producto (autorizada en controlados) | — | — | — |
| US-15, US-18 | Reportes de ventas/merma/quiebres | — | — | — |

## Calidad y despliegue (PIA)
| Requisito | Evidencia |
|---|---|
| Cobertura ≥ 80 % | `pytest` falla por debajo de 80 % (`--cov-fail-under`); resultado actual ≈ 98 % |
| Pruebas unitarias + integración | `test_dominio` (unit), `test_servicios`/`test_api`/`test_casos_csv` (integración con BD) |
| Docker Compose DB + App + Tests | `docker-compose.yml` (`db`, `app`, `tests`) |
| 12-Factor | `.env.example`, `config.py` |
| CI/CD | `.github/workflows/ci.yml` (lint, pruebas en PostgreSQL, casos CSV, compose) |
| OpenAPI | `/docs`, `/redoc`, `/openapi.json`; verificado en `test_api::test_health_y_openapi_activos` |
| ADRs | `docs/adr/ADR-001…007` |

> Nota: los IDs US-09…US-18 y BN-03…BN-10 se tomaron de los PDF del equipo y de `farmaexpress-arquitectura`; confirma la
> numeración exacta contra tu BRD final antes de entregar.
