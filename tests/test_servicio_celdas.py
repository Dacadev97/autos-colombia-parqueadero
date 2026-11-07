"""Pruebas de aceptación de la Iteración 2 (gestión de celdas), alineadas con el plan de pruebas (CP-xx)."""

import sqlite3

import pytest

from parqueadero.aplicacion.servicio_celdas import ServicioCeldas
from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.dominio.entidades import EstadoCelda, TipoVehiculo
from parqueadero.dominio.excepciones import (
    CambioEstadoCeldaInvalido,
    CeldaConHistorial,
    CeldaNoDisponible,
    CodigoCeldaInvalido,
    SinCeldasDisponibles,
    SinRegistroActivo,
)

OPERADOR = 1


@pytest.fixture
def servicio(conexion):
    return ServicioCeldas(conexion)


@pytest.fixture
def parqueo(conexion):
    return ServicioParqueo(conexion)


def estado(conexion, codigo):
    fila = conexion.execute("SELECT estado FROM celda WHERE codigo = ?", (codigo,)).fetchone()
    return fila[0] if fila else None


def id_celda(conexion, codigo):
    return conexion.execute("SELECT id_celda FROM celda WHERE codigo = ?", (codigo,)).fetchone()[0]


# HU-11: crear celdas
def test_cp13_crea_celda_disponible_con_tipo_segun_prefijo(servicio, conexion):
    celda = servicio.crear_celda(" m-06 ")
    assert (celda.codigo, celda.tipo, celda.estado) == ("M-06", TipoVehiculo.MOTO, EstadoCelda.DISPONIBLE)
    assert estado(conexion, "M-06") == "DISPONIBLE"


@pytest.mark.parametrize("codigo", ["X-01", "C1", "C-001", "C-01"])
def test_cp14_rechaza_codigo_invalido_o_repetido(servicio, conexion, codigo):
    antes = conexion.execute("SELECT COUNT(*) FROM celda").fetchone()[0]
    with pytest.raises(CodigoCeldaInvalido):
        servicio.crear_celda(codigo)
    assert conexion.execute("SELECT COUNT(*) FROM celda").fetchone()[0] == antes


# HU-12: consultar disponibilidad
def test_cp15_mapa_muestra_estado_y_vehiculo_que_ocupa_cada_celda(servicio, parqueo):
    parqueo.registrar_entrada("ABC123", OPERADOR)
    celdas = {c["codigo"]: c for c in servicio.listar()}
    assert celdas["C-01"]["estado"] == "OCUPADA" and celdas["C-01"]["placa"] == "ABC123"
    assert celdas["C-10"]["estado"] == "FUERA_DE_SERVICIO" and celdas["C-10"]["placa"] is None
    assert [c["codigo"] for c in servicio.listar(tipo="MOTO", estado="DISPONIBLE")] == [
        "M-01", "M-02", "M-03", "M-04", "M-05"
    ]


# HU-13: cambiar el estado de una celda
def test_cp16_fuera_de_servicio_y_habilitar(servicio, conexion, parqueo):
    servicio.cambiar_estado(id_celda(conexion, "C-01"), EstadoCelda.FUERA_DE_SERVICIO)
    assert estado(conexion, "C-01") == "FUERA_DE_SERVICIO"
    # La entrada automática ya no usa esa celda (integración con la Iteración 1).
    assert parqueo.registrar_entrada("ABC123", OPERADOR).celda.codigo == "C-02"

    servicio.cambiar_estado(id_celda(conexion, "C-01"), EstadoCelda.DISPONIBLE)
    assert estado(conexion, "C-01") == "DISPONIBLE"


def test_cp17_no_cambia_estado_de_celda_ocupada_ni_la_marca_ocupada_a_mano(servicio, conexion, parqueo):
    parqueo.registrar_entrada("ABC123", OPERADOR)
    with pytest.raises(CambioEstadoCeldaInvalido):
        servicio.cambiar_estado(id_celda(conexion, "C-01"), EstadoCelda.FUERA_DE_SERVICIO)
    with pytest.raises(CambioEstadoCeldaInvalido):
        servicio.cambiar_estado(id_celda(conexion, "C-02"), EstadoCelda.OCUPADA)
    assert estado(conexion, "C-01") == "OCUPADA" and estado(conexion, "C-02") == "DISPONIBLE"


def test_cp18_sin_celdas_habilitadas_se_rechaza_la_entrada(servicio, conexion, parqueo):
    for codigo in ("M-01", "M-02", "M-03", "M-04", "M-05"):
        servicio.cambiar_estado(id_celda(conexion, codigo), EstadoCelda.FUERA_DE_SERVICIO)
    with pytest.raises(SinCeldasDisponibles):
        parqueo.registrar_entrada("FGH45K", OPERADOR)


# HU-14: eliminar celdas
def test_cp19_elimina_celda_nueva_y_rechaza_celda_con_historial(servicio, conexion, parqueo):
    nueva = servicio.crear_celda("C-11")
    servicio.eliminar_celda(nueva.id)
    assert estado(conexion, "C-11") is None

    parqueo.registrar_entrada("ABC123", OPERADOR)
    parqueo.registrar_salida("ABC123", OPERADOR)
    with pytest.raises(CeldaConHistorial):
        servicio.eliminar_celda(id_celda(conexion, "C-01"))
    assert estado(conexion, "C-01") == "DISPONIBLE"


# HU-15: reubicar un vehículo dentro del parqueadero
def test_cp20_reubica_vehiculo_libera_origen_y_ocupa_destino(servicio, conexion, parqueo):
    parqueo.registrar_entrada("ABC123", OPERADOR)
    resultado = servicio.reubicar_vehiculo("abc123", "c-04")

    assert resultado.celda.codigo == "C-04"
    assert estado(conexion, "C-01") == "DISPONIBLE" and estado(conexion, "C-04") == "OCUPADA"
    assert parqueo.vehiculos_dentro()[0]["celda"] == "C-04"
    # Al salir se libera la celda nueva, no la original.
    parqueo.registrar_salida("ABC123", OPERADOR)
    assert estado(conexion, "C-04") == "DISPONIBLE"


def test_cp21_rechaza_reubicacion_invalida_sin_modificar_datos(servicio, conexion, parqueo):
    parqueo.registrar_entrada("ABC123", OPERADOR)
    parqueo.registrar_entrada("XYZ789", OPERADOR)
    with pytest.raises(CeldaNoDisponible):
        servicio.reubicar_vehiculo("ABC123", "C-02")  # ocupada
    with pytest.raises(CeldaNoDisponible):
        servicio.reubicar_vehiculo("ABC123", "M-01")  # tipo distinto
    with pytest.raises(CeldaNoDisponible):
        servicio.reubicar_vehiculo("ABC123", "C-10")  # fuera de servicio
    with pytest.raises(SinRegistroActivo):
        servicio.reubicar_vehiculo("FGH45K", "M-02")  # no está dentro
    assert parqueo.vehiculos_dentro()[-1]["celda"] in {"C-01", "C-02"}
    assert estado(conexion, "C-01") == "OCUPADA" and estado(conexion, "C-02") == "OCUPADA"


def test_cp22_falla_en_reubicacion_no_deja_estados_contradictorios(servicio, conexion, parqueo, monkeypatch):
    parqueo.registrar_entrada("ABC123", OPERADOR)
    original = servicio.celdas.actualizar_estado
    llamadas = []

    def falla_en_la_segunda(*args):
        llamadas.append(args)
        if len(llamadas) == 2:
            raise sqlite3.OperationalError("falla simulada")
        original(*args)

    monkeypatch.setattr(servicio.celdas, "actualizar_estado", falla_en_la_segunda)
    with pytest.raises(sqlite3.OperationalError):
        servicio.reubicar_vehiculo("ABC123", "C-04")

    assert parqueo.vehiculos_dentro()[0]["celda"] == "C-01"
    assert estado(conexion, "C-01") == "OCUPADA" and estado(conexion, "C-04") == "DISPONIBLE"
