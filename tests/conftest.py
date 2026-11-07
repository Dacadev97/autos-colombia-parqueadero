import pytest

from parqueadero.persistencia.conexion import abrir_conexion, crear_esquema
from parqueadero.persistencia.datos_demo import cargar_datos_demo


@pytest.fixture
def conexion():
    conexion = abrir_conexion(":memory:")
    crear_esquema(conexion)
    cargar_datos_demo(conexion)
    yield conexion
    conexion.close()
