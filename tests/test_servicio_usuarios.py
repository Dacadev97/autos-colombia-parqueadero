"""Pruebas de aceptación de la Iteración 2 (gestión de usuarios y vehículos).
Cada prueba corresponde a un caso del plan de pruebas (CP-xx) y verifica los datos guardados, no solo la respuesta."""

import pytest

from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.aplicacion.servicio_usuarios import ServicioUsuarios
from parqueadero.dominio.entidades import EstadoUsuario, TipoVehiculo
from parqueadero.dominio.excepciones import (
    DatosUsuarioInvalidos,
    DatosVehiculoInvalidos,
    DocumentoDuplicado,
    EstadoUsuarioSinCambio,
    PlacaDuplicada,
    PlacaInvalida,
    UsuarioInactivo,
    VehiculoConHistorial,
)

OPERADOR = 1


@pytest.fixture
def servicio(conexion):
    return ServicioUsuarios(conexion)


def contar(conexion, tabla):
    return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


# HU-07: registrar un usuario mensual
def test_cp01_registra_usuario_activo(servicio, conexion):
    usuario = servicio.registrar_usuario(" 1036000004 ", "Ana  María Pérez", "3001112233")

    assert usuario.id is not None and usuario.estado == EstadoUsuario.ACTIVO
    fila = conexion.execute("SELECT * FROM usuario WHERE documento = '1036000004'").fetchone()
    assert fila["nombre"] == "Ana María Pérez" and fila["estado"] == "ACTIVO"


def test_cp02_rechaza_documento_duplicado_sin_crear_registros(servicio, conexion):
    antes = contar(conexion, "usuario")
    with pytest.raises(DocumentoDuplicado):
        servicio.registrar_usuario("1036000001", "Otra Persona", "3000000000")
    assert contar(conexion, "usuario") == antes


@pytest.mark.parametrize("documento, nombre, telefono", [
    ("12AB", "Ana Pérez", "3001112233"),
    ("1036000004", "", "3001112233"),
    ("1036000004", "Ana Pérez", "300-ABC"),
])
def test_cp03_rechaza_datos_invalidos(servicio, conexion, documento, nombre, telefono):
    antes = contar(conexion, "usuario")
    with pytest.raises(DatosUsuarioInvalidos):
        servicio.registrar_usuario(documento, nombre, telefono)
    assert contar(conexion, "usuario") == antes


# HU-08: consultar y actualizar usuarios
def test_cp04_busca_por_nombre_o_documento_y_filtra_por_estado(servicio):
    assert [u["nombre"] for u in servicio.listar_usuarios(texto="restrepo")] == ["Carlos Restrepo"]
    assert servicio.listar_usuarios(texto="1036000002")[0]["vehiculos"] == 2
    assert [u["nombre"] for u in servicio.listar_usuarios(estado="INACTIVO")] == ["Marta Ruiz"]


def test_cp05_actualiza_nombre_y_telefono_sin_cambiar_documento(servicio, conexion):
    servicio.actualizar_usuario(1, "Laura Gómez Arango", "3109998877")
    fila = conexion.execute("SELECT * FROM usuario WHERE id_usuario = 1").fetchone()
    assert (fila["documento"], fila["nombre"], fila["telefono"]) == ("1036000001", "Laura Gómez Arango", "3109998877")


# HU-09: inactivar y reactivar usuarios (baja lógica)
def test_cp06_inactivar_usuario_impide_nuevas_entradas_y_conserva_historial(servicio, conexion):
    parqueo = ServicioParqueo(conexion)
    parqueo.registrar_entrada("ABC123", OPERADOR)
    parqueo.registrar_salida("ABC123", OPERADOR)

    servicio.cambiar_estado(1, EstadoUsuario.INACTIVO)

    with pytest.raises(UsuarioInactivo):
        parqueo.registrar_entrada("ABC123", OPERADOR)
    assert contar(conexion, "usuario") == 3
    assert len(parqueo.historial(placa="ABC123")) == 1


def test_cp07_vehiculo_dentro_puede_salir_aunque_el_usuario_se_inactive(servicio, conexion):
    parqueo = ServicioParqueo(conexion)
    parqueo.registrar_entrada("ABC123", OPERADOR)
    servicio.cambiar_estado(1, EstadoUsuario.INACTIVO)
    assert parqueo.registrar_salida("ABC123", OPERADOR).registro.fecha_salida is not None


def test_cp08_reactivar_usuario_permite_ingresar_y_rechaza_estado_repetido(servicio, conexion):
    with pytest.raises(EstadoUsuarioSinCambio):
        servicio.cambiar_estado(3, EstadoUsuario.INACTIVO)
    servicio.cambiar_estado(3, EstadoUsuario.ACTIVO)
    assert ServicioParqueo(conexion).registrar_entrada("JKL321", OPERADOR).celda.codigo == "C-01"


# HU-10: gestionar los vehículos de un usuario
def test_cp09_registra_vehiculo_y_deduce_el_tipo_de_la_placa(servicio, conexion):
    carro = servicio.registrar_vehiculo(1, "def-456", "Kia", "Azul")
    moto = servicio.registrar_vehiculo(1, "MNO12P", "Honda", "Rojo")

    assert (carro.placa, carro.tipo) == ("DEF456", TipoVehiculo.CARRO)
    assert moto.tipo == TipoVehiculo.MOTO
    assert {v["placa"] for v in servicio.vehiculos_de(1)} == {"ABC123", "DEF456", "MNO12P"}
    # El vehículo nuevo puede ingresar de inmediato (integración con la Iteración 1).
    assert ServicioParqueo(conexion).registrar_entrada("MNO12P", OPERADOR).celda.codigo == "M-01"


def test_cp10_rechaza_placa_duplicada_o_invalida(servicio, conexion):
    antes = contar(conexion, "vehiculo")
    with pytest.raises(PlacaDuplicada):
        servicio.registrar_vehiculo(1, "XYZ789", "Kia", "Azul")
    with pytest.raises(PlacaInvalida):
        servicio.registrar_vehiculo(1, "12345", "Kia", "Azul")
    with pytest.raises(DatosVehiculoInvalidos):
        servicio.registrar_vehiculo(1, "DEF456", "", "Azul")
    assert contar(conexion, "vehiculo") == antes


def test_cp11_actualiza_marca_y_color(servicio, conexion):
    servicio.actualizar_vehiculo(1, "Renault", "Plata")
    assert conexion.execute("SELECT color FROM vehiculo WHERE id_vehiculo = 1").fetchone()[0] == "Plata"


def test_cp12_elimina_vehiculo_sin_historial_y_rechaza_con_historial(servicio, conexion):
    nuevo = servicio.registrar_vehiculo(1, "DEF456", "Kia", "Azul")
    servicio.eliminar_vehiculo(nuevo.id)
    assert conexion.execute("SELECT COUNT(*) FROM vehiculo WHERE placa = 'DEF456'").fetchone()[0] == 0

    ServicioParqueo(conexion).registrar_entrada("ABC123", OPERADOR)
    with pytest.raises(VehiculoConHistorial):
        servicio.eliminar_vehiculo(1)
    assert conexion.execute("SELECT COUNT(*) FROM vehiculo WHERE placa = 'ABC123'").fetchone()[0] == 1
