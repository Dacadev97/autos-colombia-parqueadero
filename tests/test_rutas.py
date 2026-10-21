import pytest

from parqueadero import create_app


@pytest.fixture
def cliente(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "prueba.db"), "TESTING": True})
    cliente = app.test_client()
    cliente.post("/login", data={"usuario": "operador", "clave": "autos2026"})
    return cliente


def test_requiere_sesion(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "prueba.db")})
    respuesta = app.test_client().get("/")
    assert respuesta.status_code == 302 and "/login" in respuesta.location


def test_rechaza_credenciales_invalidas(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "prueba.db")})
    respuesta = app.test_client().post("/login", data={"usuario": "operador", "clave": "mala"})
    assert "Usuario o contraseña incorrectos" in respuesta.get_data(as_text=True)


def test_flujo_entrada_y_salida(cliente):
    html = cliente.post("/entrada", data={"placa": "ABC123", "celda": "", "observacion": ""}).get_data(as_text=True)
    assert "Entrada registrada correctamente" in html and "C-01" in html

    assert "ABC123" in cliente.get("/").get_data(as_text=True)

    html = cliente.post("/salida", data={"placa": "ABC123", "observacion": ""}).get_data(as_text=True)
    assert "Salida registrada correctamente" in html


def test_rechazo_conserva_los_datos_digitados(cliente):
    html = cliente.post(
        "/entrada", data={"placa": "QQQ111", "celda": "", "observacion": "Sin espejo"}
    ).get_data(as_text=True)
    assert "Entrada rechazada (RN-01)" in html
    assert 'value="QQQ111"' in html and "Sin espejo" in html
