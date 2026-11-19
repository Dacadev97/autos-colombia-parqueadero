"""Pruebas de integración de las rutas web de la Iteración 3: CP-37 a CP-40."""
import pytest

from parqueadero import create_app


def _cliente(tmp_path, usuario, clave):
    app = create_app({"DATABASE": str(tmp_path / "prueba.db"), "TESTING": True})
    cliente = app.test_client()
    cliente.post("/login", data={"usuario": usuario, "clave": clave})
    return cliente


@pytest.fixture
def operador(tmp_path):
    return _cliente(tmp_path, "operador", "autos2026")


@pytest.fixture
def admin(tmp_path):
    return _cliente(tmp_path, "admin", "admin2026")


# CP-37 (HU-16): el operador registra el pago y ve el recibo.
def test_cp37_registrar_pago_muestra_recibo(operador):
    respuesta = operador.post("/pagos", data={"placa": "ABC123", "periodo": "2027-01", "medio": "EFECTIVO",
                                              "referencia": ""})
    assert respuesta.status_code == 302
    html = operador.get(respuesta.location).get_data(as_text=True)
    assert "Pago registrado: recibo REC-" in html and "$180.000" in html and "2027-01" in html


# CP-38: un rechazo conserva lo digitado y muestra el código de la regla.
def test_cp38_rechazo_conserva_lo_digitado(operador):
    html = operador.post("/pagos", data={"placa": "ABC123", "periodo": "2027-01", "medio": "TRANSFERENCIA",
                                         "referencia": ""}).get_data(as_text=True)
    assert "Pago rechazado (RN-17)" in html and 'value="2027-01"' in html


# CP-39 (RNF-09): solo el administrador anula pagos y cambia tarifas.
def test_cp39_operador_no_anula_ni_cambia_tarifas(operador):
    assert operador.post("/pagos/1/anular", data={"motivo": "Prueba de permisos"}).status_code == 403
    assert operador.post("/tarifas", data={"tipo": "CARRO", "valor": "190000"}).status_code == 403
    assert "Anular pago" not in operador.get("/pagos/1").get_data(as_text=True)


def test_cp40_administrador_anula_y_actualiza_tarifa(admin):
    html = admin.post("/pagos/1/anular", data={"motivo": "Cobro duplicado"}, follow_redirects=True).get_data(as_text=True)
    assert "REC-000001 quedó anulado" in html and "Anulado" in html
    html = admin.post("/tarifas", data={"tipo": "MOTO", "valor": "75.000"}, follow_redirects=True).get_data(as_text=True)
    assert "Tarifa mensual de moto actualizada a $75.000" in html


def test_entrada_rechazada_por_mensualidad_desde_la_interfaz(operador):
    operador.post("/usuarios/1/vehiculos", data={"placa": "DEF456", "marca": "Kia", "color": "Azul"})
    html = operador.post("/entrada", data={"placa": "DEF456", "celda": "", "observacion": ""}).get_data(as_text=True)
    assert "RN-19" in html and "no tiene pagada la mensualidad" in html
