"""Pruebas de aceptación de la Iteración 1, alineadas con los criterios Dado-Cuando-Entonces de las historias de usuario."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.dominio.entidades import EstadoCelda
from parqueadero.dominio.excepciones import (
    CeldaNoDisponible,
    PlacaInvalida,
    SinCeldasDisponibles,
    SinRegistroActivo,
    UsuarioInactivo,
    VehiculoNoRegistrado,
    VehiculoYaDentro,
)
from parqueadero.persistencia.conexion import abrir_conexion, crear_esquema
from parqueadero.persistencia.datos_demo import cargar_datos_demo

OPERADOR = 1


class RelojFalso:
    def __init__(self):
        self.ahora = datetime(2026, 10, 21, 8, 0, 0)

    def __call__(self):
        return self.ahora

    def avanzar(self, minutos):
        self.ahora += timedelta(minutes=minutos)


@pytest.fixture
def reloj():
    return RelojFalso()


@pytest.fixture
def conexion():
    conexion = abrir_conexion(":memory:")
    crear_esquema(conexion)
    cargar_datos_demo(conexion)
    yield conexion
    conexion.close()


@pytest.fixture
def servicio(conexion, reloj):
    return ServicioParqueo(conexion, reloj)


def estado_celda(conexion, codigo):
    return conexion.execute("SELECT estado FROM celda WHERE codigo = ?", (codigo,)).fetchone()[0]


# HU-01: registrar la entrada de un vehículo
def test_entrada_valida_asigna_celda_y_la_ocupa(servicio, conexion):
    resultado = servicio.registrar_entrada("abc-123", OPERADOR, observacion="Rayón puerta trasera")

    assert resultado.vehiculo.placa == "ABC123"
    assert resultado.celda.codigo == "C-01"
    assert resultado.registro.fecha_entrada == datetime(2026, 10, 21, 8, 0, 0)
    assert resultado.registro.fecha_salida is None
    assert resultado.registro.observacion_entrada == "Rayón puerta trasera"
    assert estado_celda(conexion, "C-01") == EstadoCelda.OCUPADA.value


def test_entrada_en_celda_elegida_por_el_operador(servicio):
    resultado = servicio.registrar_entrada("XYZ789", OPERADOR, codigo_celda="c-05")
    assert resultado.celda.codigo == "C-05"


def test_moto_recibe_celda_de_moto(servicio):
    assert servicio.registrar_entrada("FGH45K", OPERADOR).celda.codigo == "M-01"


# HU-02: rechazar entradas que incumplen las reglas
def test_rechaza_placa_con_formato_invalido(servicio):
    with pytest.raises(PlacaInvalida):
        servicio.registrar_entrada("12AB", OPERADOR)


def test_rechaza_vehiculo_no_registrado(servicio):
    with pytest.raises(VehiculoNoRegistrado):
        servicio.registrar_entrada("QQQ111", OPERADOR)


def test_rechaza_vehiculo_de_usuario_inactivo(servicio):
    with pytest.raises(UsuarioInactivo):
        servicio.registrar_entrada("JKL321", OPERADOR)


def test_rechaza_vehiculo_que_ya_esta_dentro(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR)
    with pytest.raises(VehiculoYaDentro):
        servicio.registrar_entrada("ABC123", OPERADOR)


def test_rechaza_celda_ocupada_fuera_de_servicio_o_incompatible(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR, codigo_celda="C-01")
    with pytest.raises(CeldaNoDisponible):
        servicio.registrar_entrada("XYZ789", OPERADOR, codigo_celda="C-01")
    with pytest.raises(CeldaNoDisponible):
        servicio.registrar_entrada("XYZ789", OPERADOR, codigo_celda="C-10")
    with pytest.raises(CeldaNoDisponible):
        servicio.registrar_entrada("XYZ789", OPERADOR, codigo_celda="M-01")


def test_rechaza_entrada_sin_celdas_disponibles(servicio, conexion):
    conexion.execute("UPDATE celda SET estado = 'OCUPADA' WHERE tipo = 'MOTO'")
    with pytest.raises(SinCeldasDisponibles):
        servicio.registrar_entrada("FGH45K", OPERADOR)


def test_rechazo_no_modifica_datos(servicio, conexion):
    with pytest.raises(VehiculoNoRegistrado):
        servicio.registrar_entrada("QQQ111", OPERADOR)
    assert conexion.execute("SELECT COUNT(*) FROM registro_parqueo").fetchone()[0] == 0


# HU-03: registrar la salida de un vehículo
def test_salida_cierra_registro_y_libera_celda(servicio, conexion, reloj):
    servicio.registrar_entrada("ABC123", OPERADOR)
    reloj.avanzar(90)

    resultado = servicio.registrar_salida("ABC123", OPERADOR, observacion="Usuario reporta golpe en parachoques")

    assert resultado.registro.fecha_salida == datetime(2026, 10, 21, 9, 30, 0)
    assert resultado.registro.observacion_salida == "Usuario reporta golpe en parachoques"
    assert estado_celda(conexion, "C-01") == EstadoCelda.DISPONIBLE.value
    assert servicio.vehiculos_dentro() == []


def test_vehiculo_puede_volver_a_ingresar_despues_de_salir(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR)
    servicio.registrar_salida("ABC123", OPERADOR)
    servicio.registrar_entrada("ABC123", OPERADOR)
    assert len(servicio.historial(placa="ABC123")) == 2


# HU-04: rechazar salidas sin entrada activa
def test_rechaza_salida_sin_entrada_activa(servicio):
    with pytest.raises(SinRegistroActivo):
        servicio.registrar_salida("XYZ789", OPERADOR)


def test_rechaza_salida_duplicada(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR)
    servicio.registrar_salida("ABC123", OPERADOR)
    with pytest.raises(SinRegistroActivo):
        servicio.registrar_salida("ABC123", OPERADOR)


# HU-05: consultar vehículos dentro e historial
def test_consulta_vehiculos_dentro_y_resumen_de_celdas(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR)
    servicio.registrar_entrada("FGH45K", OPERADOR)

    placas = {r["placa"] for r in servicio.vehiculos_dentro()}
    resumen = servicio.resumen_celdas()

    assert placas == {"ABC123", "FGH45K"}
    assert resumen["CARRO"] == {"DISPONIBLE": 8, "OCUPADA": 1, "FUERA_DE_SERVICIO": 1}
    assert resumen["MOTO"]["OCUPADA"] == 1


def test_historial_filtra_por_fecha(servicio):
    servicio.registrar_entrada("ABC123", OPERADOR)
    assert len(servicio.historial(desde="2026-10-21", hasta="2026-10-21")) == 1
    assert servicio.historial(desde="2026-10-22") == []


# RNF-03 y modelo físico: la base de datos también protege las reglas
def test_indice_unico_impide_dos_registros_activos_por_vehiculo(conexion):
    insertar = (
        "INSERT INTO registro_parqueo (id_vehiculo, id_celda, id_operador_entrada, fecha_entrada) "
        "VALUES (1, ?, 1, '2026-10-21 08:00:00')"
    )
    conexion.execute(insertar, (1,))
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(insertar, (2,))


def test_falla_en_la_operacion_no_deja_estados_contradictorios(servicio, conexion, monkeypatch):
    def falla(*_args):
        raise sqlite3.OperationalError("falla simulada")

    monkeypatch.setattr(servicio.celdas, "actualizar_estado", falla)
    with pytest.raises(sqlite3.OperationalError):
        servicio.registrar_entrada("ABC123", OPERADOR)

    assert conexion.execute("SELECT COUNT(*) FROM registro_parqueo").fetchone()[0] == 0
    assert estado_celda(conexion, "C-01") == EstadoCelda.DISPONIBLE.value
