"""Pruebas de contrato de la API: 200/201 + 400/404/409/422."""
import pytest


def _nuevo(client, **kw):
    body = {"comprador_id": "FAR-C001", "lineas": [{"recurso_id": "FAR-P009", "cantidad": 3}], "autorizado": True}
    body.update(kw)
    return client.post("/pedidos", json=body)


def test_health_y_openapi_activos(client):
    assert client.get("/health").json() == {"status": "ok"}
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "FarmaExpress API"
    assert "/pedidos/{pedido_id}/validar" in spec["paths"]
    assert client.get("/docs").status_code == 200  # Swagger UI
    assert client.get("/redoc").status_code == 200


def test_crear_devuelve_201_con_total_decimal(client):
    r = _nuevo(client)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "CREADO" and cuerpo["total"] == "3057.00"
    assert set(cuerpo["acciones_permitidas"]) == {"validar", "cancelar"}


def test_flujo_completo_200(client):
    pid = _nuevo(client).json()["id"]
    for accion, estado in [("validar", "VALIDADO"), ("preparar", "PREPARADO"), ("entregar", "ENTREGADO")]:
        r = client.post(f"/pedidos/{pid}/{accion}")
        assert r.status_code == 200 and r.json()["estado"] == estado
    assert client.get("/productos/FAR-P009").json()["stock"] == 34
    eventos = client.get(f"/pedidos/{pid}/eventos").json()
    assert [e["evento"] for e in eventos][-1] == "PedidoEntregado"
    assert client.get(f"/pedidos/{pid}").json()["acciones_permitidas"] == []


@pytest.mark.parametrize("cantidad", [0, -2])
def test_400_cantidad_invalida(client, cantidad):
    r = _nuevo(client, lineas=[{"recurso_id": "FAR-P009", "cantidad": cantidad}])
    assert r.status_code == 400 and r.json()["codigo"] == "DATOS_INVALIDOS"


def test_400_cuerpo_mal_formado(client):
    assert client.post("/pedidos", json={"lineas": "x"}).status_code == 400
    fraccion = {"comprador_id": "FAR-C001", "lineas": [{"recurso_id": "FAR-P001", "cantidad": 1.5}]}
    assert client.post("/pedidos", json=fraccion).status_code == 400


def test_404_recursos_inexistentes(client):
    assert client.get("/pedidos/NOPE").status_code == 404
    assert client.post("/pedidos/NOPE/validar").status_code == 404
    assert client.get("/pedidos/NOPE/eventos").status_code == 404
    assert client.get("/compradores/NOPE").status_code == 404
    assert client.get("/productos/NOPE").status_code == 404
    assert _nuevo(client, comprador_id="NOPE").status_code == 404
    assert _nuevo(client, lineas=[{"recurso_id": "NOPE", "cantidad": 1}]).status_code == 404


def test_409_transicion_invalida(client):
    pid = _nuevo(client).json()["id"]
    r = client.post(f"/pedidos/{pid}/entregar")  # salto de estado
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLICTO_DE_ESTADO"
    client.post(f"/pedidos/{pid}/validar")
    assert client.post(f"/pedidos/{pid}/validar").status_code == 409  # repetir aprobación
    assert client.post(f"/pedidos/{pid}/cancelar").status_code == 409  # ya no se cancela
    assert client.post(f"/pedidos/{pid}/lineas", json={"recurso_id": "FAR-P001", "cantidad": 1}).status_code == 409


def test_409_pedido_duplicado_no_aplica_a_ids_generados(client):
    assert _nuevo(client).json()["id"] != _nuevo(client).json()["id"]


def test_422_regla_de_negocio(client):
    pid = _nuevo(client, autorizado=False).json()["id"]
    r = client.post(f"/pedidos/{pid}/validar")
    assert r.status_code == 422
    assert r.json()["reglas_incumplidas"] == ["autorizacion"]
    inactivo = next(c for c in client.get("/compradores").json() if not c["activo"])
    pid2 = _nuevo(client, comprador_id=inactivo["actor_id"]).json()["id"]
    assert "cliente_activo" in client.post(f"/pedidos/{pid2}/validar").json()["reglas_incumplidas"]


def test_evaluacion_expone_las_specifications(client):
    pref = next(c for c in client.get("/compradores").json() if c["es_preferente"] and c["activo"])
    pid = _nuevo(client, comprador_id=pref["actor_id"]).json()["id"]
    ev = client.get(f"/pedidos/{pid}/evaluacion").json()
    assert ev["puede_procesarse"] is True and ev["beneficio_referencia"] is True
    promo = _nuevo(client, comprador_id=pref["actor_id"], promocion_activa=True).json()["id"]
    assert client.get(f"/pedidos/{promo}/evaluacion").json()["beneficio_referencia"] is False


def test_agregar_linea_y_filtrar_por_estado(client):
    pid = client.post("/pedidos", json={"comprador_id": "FAR-C001", "autorizado": True}).json()["id"]
    r = client.post(f"/pedidos/{pid}/lineas", json={"recurso_id": "FAR-P001", "cantidad": 2})
    assert r.status_code == 200 and r.json()["total"] == "902.00"
    client.post(f"/pedidos/{pid}/cancelar")
    ids = [p["id"] for p in client.get("/pedidos", params={"estado": "CANCELADO"}).json()]
    assert ids == [pid]


def test_catalogo_listados(client):
    assert len(client.get("/compradores").json()) == 40
    assert len(client.get("/productos").json()) == 20
    assert client.get("/compradores/FAR-C001").json()["nombre"] == "Comprador 01"
