# Matriz de trazabilidad: BRD → regla → componente → prueba

Fuente única de IDs: [`BRD_final.md`](BRD_final.md) v2.0 (BN-01…BN-14, US-01…US-26, RN-01…RN-09, S-x, R-x).
Las rutas de prueba se verifican automáticamente (ver *Verificación* al final).
Leyenda: **✔** implementado y probado · **◐** parcial · **—** backlog (BRD §9.6).

## 1. Necesidades del negocio (BN)
| BN | Necesidad (resumen) | Historias | Reglas | Estado |
|---|---|---|---|---|
| BN-01 | Receta completa y vigente antes de vender controlados | US-02, US-03, US-21 | RN-04 | ◐ valida existencia y vigencia ≤ 30 días; no captura paciente/médico/cédula |
| BN-02 | Impedir venta de caducados / lotes retirados | US-07, US-08 | — | — |
| BN-03 | Punto de reorden por rotación | US-11 | — | — |
| BN-04 | Alerta de resurtido bajo mínimo | US-12, US-13, US-14 | — | — (`PedidoPreparado` es el punto de enganche) |
| BN-05 | Alertas de caducidad 90/60/30 | US-09, US-10 | — | — |
| BN-06 | Bloqueo inmediato de lote retirado | US-08 | — | — |
| BN-07 | Visibilidad entre sucursales | US-15, US-16 | — | — |
| BN-08 | Conteo cíclico y diferencias | US-17 | — | — |
| BN-09 | Reportes | US-18 | — | — |
| BN-10 | Autorización restringida por rol | US-04, US-06 | RN-05, S-2 | ◐ autorización como bandera; sin roles |
| BN-11 | Ciclo de vida del pedido | US-19, US-20, US-22, US-23, US-24, US-25 | RN-06, RN-07, RN-08 | ✔ |
| BN-12 | Validación previa al proceso | US-20, US-21 | RN-01, RN-03, RN-04, RN-05 | ✔ |
| BN-13 | Beneficio de referencia | US-23 | RN-02 | ✔ |
| BN-14 | Bitácora auditable de estados | US-26 | RN-09 | ✔ |

## 2. Historias de usuario → componente → prueba
| US | Regla(s) | Componente (código) | Endpoint | Pruebas |
|---|---|---|---|---|
| US-19 | RN-08 | `Pedido.crear`, `Cantidad`, `Dinero`, `ServicioPedidos.crear_pedido`, `PedidoIn` | `POST /pedidos`, `POST /pedidos/{id}/lineas` | `test_api::test_crear_devuelve_201_con_total_decimal` · `test_api::test_400_cantidad_invalida` · `test_api::test_404_recursos_inexistentes` · `test_api::test_agregar_linea_y_filtrar_por_estado` · `test_dominio::test_total_con_decimal` · `test_dominio::test_cantidad_rechaza_no_positivos_o_no_enteros` · `test_servicios::test_cantidad_invalida` |
| US-20 | RN-01, RN-03, RN-06 | `PUEDE_VALIDARSE`, `Pedido.validar` | `POST /pedidos/{id}/validar` | `test_dominio::test_precondiciones_de_validacion` · `test_dominio::test_puede_procesarse_requiere_las_tres_condiciones` · `test_servicios::test_flujo_completo_persiste_estado_stock_y_eventos` · `test_api::test_flujo_completo_200` |
| US-21 | RN-01, RN-03, RN-04, RN-05, RN-07 | `Specification.fallos`, `ReglaDeNegocioIncumplida`, `api/errores.py` | `POST /pedidos/{id}/validar` → 422 | `test_api::test_422_regla_de_negocio` · `test_dominio::test_fallos_explican_que_regla_no_se_cumple` · `test_dominio::test_validar_con_regla_incumplida_es_422_y_no_cambia_estado` · `test_servicios::test_stock_insuficiente_impide_validar` · `test_servicios::test_producto_deshabilitado_impide_validar` · `test_dominio::test_controlado_exige_receta_y_autorizacion_por_limite` · `test_casos_csv::test_120_casos_coinciden_con_el_oraculo` |
| US-22 | RN-03, RN-06, RN-09 | `PUEDE_PREPARARSE`, `Pedido.preparar`, `Producto.descontar` | `POST /pedidos/{id}/preparar` | `test_dominio::test_flujo_completo_emite_eventos_en_orden_y_descuenta_stock` · `test_dominio::test_preparar_sin_stock_falla_y_no_descuenta` · `test_dominio::test_descontar` · `test_servicios::test_flujo_completo_persiste_estado_stock_y_eventos` |
| US-23 | RN-02, RN-06 | `BENEFICIO_REFERENCIA`, `Pedido.entregar`, `PedidoEntregado` | `POST /pedidos/{id}/entregar`, `GET /pedidos/{id}/evaluacion` | `test_dominio::test_beneficio_referencia` · `test_api::test_evaluacion_expone_las_specifications` · `test_dominio::test_flujo_completo_emite_eventos_en_orden_y_descuenta_stock` |
| US-24 | RN-06 | `Pedido.cancelar`, `PedidoCancelado` | `POST /pedidos/{id}/cancelar` | `test_dominio::test_cancelar_emite_evento` · `test_dominio::test_cancelacion_solo_desde_creado` · `test_servicios::test_cancelar_y_transiciones_invalidas` · `test_casos_csv::test_20_transiciones_con_estado_final_o_excepcion` |
| US-25 | RN-06, RN-07 | `MaquinaDeEstados`, `TransicionInvalida` | todas las acciones → 409 | `test_dominio::test_matriz_completa_solo_4_transiciones_legales` · `test_dominio::test_transicion_ilegal_tiene_prioridad_sobre_reglas` · `test_dominio::test_no_se_valida_dos_veces` · `test_api::test_409_transicion_invalida` |
| US-26 | RN-09 | `PublicadorDeEventos`, `SqlEventos`, `BusDeEventosEnMemoria` | `GET /pedidos/{id}/eventos` | `test_servicios::test_eventos_no_se_publican_si_la_operacion_falla` · `test_servicios::test_suscriptor_roto_no_revierte_la_operacion` · `test_api::test_flujo_completo_200` |

## 3. Cobertura de las historias originales (US-01…US-18)
| US | Estado | Qué hay / qué falta | Pruebas |
|---|---|---|---|
| US-01 | ◐ | Se descuenta existencia al preparar (por producto, no por lote); no hay ticket. | `test_servicios::test_flujo_completo_persiste_estado_stock_y_eventos` |
| US-02 | — | Sólo se guarda `receta_fecha`; falta captura de paciente, médico y cédula (backlog 1). | — |
| US-03 | ◐ | Vigencia ≤ 30 días y presencia de receta; falta validar datos obligatorios. | `test_dominio::test_receta_vigente_30_dias` · `test_dominio::test_controlado_exige_receta_y_autorizacion_por_limite` |
| US-04 | ◐ | Límite 10 piezas / $3,000 exige autorización (bandera). Falta flujo de aprobación por rol. | `test_dominio::test_limite_controlado_10_piezas_o_3000` · `test_dominio::test_controlado_exige_receta_y_autorizacion_por_limite` |
| US-05…US-18 | — | Backlog (BRD §9.6). | — |

## 4. Reglas del paquete de datos → BRD
| Regla del paquete | Equivale a | Prueba contra los CSV |
|---|---|---|
| `puede_procesarse` | RN-01 | `test_casos_csv::test_120_casos_coinciden_con_el_oraculo` (60 casos `validar_operacion`) |
| `beneficio_referencia` | RN-02 (BN-13) | ídem (60 casos `evaluar_beneficio`) |
| Transiciones `aprobar`, `completar`, `cancelar`, `repetir_aprobacion`, `saltar_estado` | RN-06, RN-07 | `test_casos_csv::test_20_transiciones_con_estado_final_o_excepcion` · `test_casos_csv::test_transicion_coincide_con_oraculo_de_reglas` |
| ≥ 3 Specifications con AND/OR/NOT | RN-01…RN-05 | `test_dominio::test_operadores_and_or_not_son_composables` · `test_arquitectura::test_hay_al_menos_tres_specifications_hoja` |

## 5. Calidad y despliegue (PIA)
| Requisito | Evidencia |
|---|---|
| Cobertura ≥ 80 % | `pyproject.toml` (`--cov-fail-under=80`) y CI; resultado ≈ 98 % |
| Pruebas unitarias + integración | `test_dominio` (unitarias) · `test_servicios`, `test_api`, `test_casos_csv` (integración con BD) · `test_arquitectura` |
| Docker Compose DB + App + Tests | `docker-compose.yml` |
| 12-Factor | `.env.example`, `src/farmaexpress/config.py` |
| CI/CD | `.github/workflows/ci.yml` (ejecución verde en GitHub Actions) |
| OpenAPI | `/docs`, `/redoc`, `/openapi.json` · `test_api::test_health_y_openapi_activos` |
| ADRs | `docs/adr/ADR-001…007` |

## Verificación
Todas las referencias `archivo::prueba` de este documento existen en `tests/` y todos los IDs (BN, US, RN) existen en `BRD_final.md`:
```bash
python scripts/verificar_trazabilidad.py
```
(también corre en CI).
