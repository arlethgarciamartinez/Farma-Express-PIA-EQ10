# ADR-008 — Mensajes en lenguaje claro (BN-15, US-27, RN-10)

**Estado:** Aceptada · Origen: retroalimentación de la revisión — *"el comentario de respuesta debe poder entenderlo cualquier
usuario, incluso quien no conoce el proyecto; póngase en los zapatos de un cliente real"*.

## Contexto
Las primeras respuestas eran correctas pero técnicas: `reglas_incumplidas: ["cliente_activo"]`, `CONFLICTO_DE_ESTADO`,
`Input should be greater than 0` (en inglés). Sólo un desarrollador las entiende.

## Decisión
1. Toda respuesta contesta tres preguntas: **qué pasó**, **por qué** y **qué hacer ahora**.
2. Los campos legibles van **primero** en el JSON y los técnicos se **conservan** al final (compatibilidad y depuración):

| Respuesta | Campos en lenguaje claro | Campos técnicos (sin cambios) |
|---|---|---|
| Error 400/404/409/422 | `mensaje`, `que_hacer`, `motivos[]` | `codigo`, `detalle`, `reglas_incumplidas[]` |
| Pedido (200/201) | `resumen`, `siguiente_paso` | `estado`, `acciones_permitidas`, … |
| Evaluación | `conclusion_procesamiento`, `conclusion_beneficio`, `motivos_*` | `puede_procesarse`, `fallos_*`, … |
| Eventos | `descripcion` | `evento`, `datos` |
| CSV de casos | columna `explicacion` | `resultado_alumno`, `evidencia` |

3. La redacción vive en **`application/mensajes.py`**, no en el dominio: el dominio sólo conoce *nombres de regla*; las
   oraciones son presentación. Está en `application` (y no en `api`) porque la usan tanto la API como el ejecutor de casos,
   y `infrastructure` no puede importar `api` (ADR-001).
4. Los errores de formato de Pydantic (en inglés) se traducen a español (`explicar_validacion`).
5. Un test (`sin_jerga`) falla si un mensaje contiene nombres en `snake_case`, códigos técnicos, nombres de clases o frases
   en inglés. Así nadie reintroduce jerga sin que el CI se ponga en rojo.

## Alternativas descartadas
- *Reemplazar los campos técnicos*: rompe a quien ya consume la API y quita información útil al depurar.
- *Textos dentro de cada Specification*: mezcla presentación con reglas y no cubre las composiciones (`NOT …`).

## Consecuencias
Una regla nueva sin texto no rompe nada (cae en un mensaje genérico), pero el test `test_todas_las_reglas_conocidas_tienen_texto_claro`
obliga a mantener el catálogo al día. El idioma es español; para otro idioma bastaría con un segundo catálogo.
