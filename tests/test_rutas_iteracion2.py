import sqlite3

import pytest

from parqueadero import create_app
from parqueadero.persistencia.conexion import abrir_conexion, crear_esquema


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


def test_flujo_registrar_usuario_y_vehiculo(operador):
    respuesta = operador.post("/usuarios", data={"documento": "1036000004", "nombre": "Ana Pérez", "telefono": "3001112233"})
    assert respuesta.status_code == 302
    html = operador.get(respuesta.location).get_data(as_text=True)
    assert "Usuario Ana Pérez registrado" in html

    html = operador.post(respuesta.location + "/vehiculos", data={"placa": "DEF456", "marca": "Kia", "color": "Azul"},
                         follow_redirects=True).get_data(as_text=True)
    assert "Vehículo DEF456 (carro) registrado" in html


def test_rechazo_de_usuario_conserva_lo_digitado(operador):
    html = operador.post("/usuarios", data={"documento": "1036000001", "nombre": "Repetido", "telefono": "3000000000"}
                         ).get_data(as_text=True)
    assert "Registro rechazado (RN-07)" in html and 'value="Repetido"' in html


def test_operador_no_puede_modificar_el_catalogo_de_celdas(operador):
    assert operador.post("/celdas", data={"codigo": "C-11"}).status_code == 403
    assert "Reubicar vehículo" in operador.get("/celdas").get_data(as_text=True)


def test_administrador_crea_y_deshabilita_celdas(admin):
    html = admin.post("/celdas", data={"codigo": "C-11"}, follow_redirects=True).get_data(as_text=True)
    assert "Celda C-11 creada y disponible" in html
    html = admin.post("/celdas/1/estado", data={"estado": "FUERA_DE_SERVICIO"}, follow_redirects=True).get_data(as_text=True)
    assert "La celda C-01 quedó fuera de servicio" in html


def test_reubicacion_desde_la_interfaz(operador):
    operador.post("/entrada", data={"placa": "ABC123", "celda": "", "observacion": ""})
    html = operador.post("/celdas/reubicar", data={"placa": "ABC123", "destino": "C-02"}, follow_redirects=True
                         ).get_data(as_text=True)
    assert "reubicado en la celda C-02" in html


def test_migra_base_de_la_iteracion_1_sin_perder_datos(tmp_path):
    ruta = str(tmp_path / "antigua.db")
    conexion = sqlite3.connect(ruta)
    conexion.execute("CREATE TABLE operador (id_operador INTEGER PRIMARY KEY, usuario TEXT, nombre TEXT, clave_hash TEXT)")
    conexion.execute("INSERT INTO operador VALUES (1, 'operador', 'Operador', 'x')")
    conexion.commit()
    conexion.close()

    conexion = abrir_conexion(ruta)
    crear_esquema(conexion)
    assert conexion.execute("SELECT rol FROM operador WHERE id_operador = 1").fetchone()[0] == "OPERADOR"
