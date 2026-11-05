# Lista de verificación de entrega del PIA

Estado: ✔ listo en el repo · ◐ parcial · ☐ lo hace el equipo.

| Requisito del PIA | Evidencia en el repo | Estado |
|---|---|---|
| Misma empresa/caso (FarmaExpress) que U2 y U3 | `docs/u2/`, `docs/u3/`, README | ✔ |
| BRD, User Stories/Gherkin, BPMN y glosario como base | `docs/BRD_final.md` (v2.0), `docs/u2/BRD_v1.pdf`, `User_Stories_Gherkin.pdf`, `BPMN.pdf`, `Glosario.pdf` | ✔ |
| ≥ 15 historias con Gherkin | 27 (18 de v1 + 9 en BRD §9.5) | ✔ |
| Diseño DDD / UML | `docs/diagramas.md` (clases, capas, secuencias), `docs/u3/*.png`, `docs/u3/Reporte_Diseno_Arquitectural.pdf` | ✔ |
| DDD en capas domain / application / infrastructure / api | `src/farmaexpress/` + `tests/test_arquitectura.py` | ✔ |
| ≥ 3 Specifications con AND/OR/NOT | `domain/specifications.py`, `domain/reglas.py` | ✔ |
| Máquina de estados + transiciones inválidas | `domain/state_machine.py`, `TestMaquinaDeEstados` (matriz 5×4) | ✔ |
| Domain Events | `domain/events.py`, `infrastructure/bus.py`, `GET /pedidos/{id}/eventos` | ✔ |
| API REST + OpenAPI/Swagger | `/docs`, `/redoc`, `/openapi.json` | ✔ |
| Contrato 200/201/400/404/409/422 | ADR-006, `tests/test_api.py` | ✔ |
| ADRs | `docs/adr/ADR-001…008` | ✔ |
| Respuestas comprensibles para cualquier usuario (retroalimentación) | ADR-008, `application/mensajes.py`, `tests/test_mensajes.py` | ✔ |
| Pruebas unitarias + integración, cobertura ≥ 80 % | 151 pruebas · ≈ 98 % (log de CI; la captura de 97 corresponde a la corrida anterior) | ✔ |
| 120 casos y 20 transiciones del paquete ejecutados con evidencia | `resultados/*.csv` (generados por `ejecutor_casos`) | ✔ |
| Docker Compose DB + App + Tests | `docker-compose.yml` (CI lo ejecuta en verde) | ✔ |
| 12-Factor / `.env.example` | `.env.example`, `config.py` | ✔ |
| CI/CD en `.github/workflows/` | `ci.yml` (ejecuciones en verde) | ✔ |
| Matriz de trazabilidad BRD → regla → componente → prueba | `docs/trazabilidad.md` + `scripts/verificar_trazabilidad.py` | ✔ |
| README | raíz del repo | ✔ |
| Acceso del docente al repositorio | Settings → Collaborators (repo es público) | ☐ |
| Subir entregables a la plataforma y compartir el enlace | enlace del repo | ☐ |
| Capturas: Actions en verde, pytest 97 passed, Swagger | tomar antes de entregar | ☐ |
| Contribuciones de los 3 integrantes visibles | cada quien hace al menos un commit con su usuario | ☐ |
| Ensayar la demostración | `docs/GUION_DEMO.md` | ☐ |

## Brechas que debes poder explicar (honestas)
1. Receta: sólo se valida existencia y vigencia ≤ 30 días (BN-01 parcial).
2. Autorización: bandera booleana, sin roles (BN-10 parcial).
3. Sin lotes/caducidad/resurtido/transferencias/reportes: backlog priorizado en BRD §9.6.
4. El BPMN y los diagramas de U3 describen la venta con lotes; el código implementa el pedido (ADR-005).
