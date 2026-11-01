"""Casos de uso de la Iteración 2: gestión de celdas (catálogo, disponibilidad y reubicación)."""

import sqlite3

from parqueadero.aplicacion.servicio_parqueo import ResultadoOperacion
from parqueadero.dominio.entidades import (
    Celda,
    EstadoCelda,
    TipoVehiculo,
    normalizar_placa,
    tipo_por_codigo_celda,
)
from parqueadero.dominio.excepciones import (
    CambioEstadoCeldaInvalido,
    CeldaConHistorial,
    CeldaNoDisponible,
    CeldaNoEncontrada,
    CodigoCeldaInvalido,
    SinRegistroActivo,
    VehiculoNoRegistrado,
)
from parqueadero.persistencia.repositorios import (
    RepositorioCeldas,
    RepositorioRegistros,
    RepositorioVehiculos,
)


class ServicioCeldas:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion
        self.celdas = RepositorioCeldas(conexion)
        self.registros = RepositorioRegistros(conexion)
        self.vehiculos = RepositorioVehiculos(conexion)

    def obtener_celda(self, id_celda: int) -> Celda:
        celda = self.celdas.buscar_por_id(id_celda)
        if celda is None:
            raise CeldaNoEncontrada("La celda solicitada no existe.")
        return celda

    def listar(self, tipo: str | None = None, estado: str | None = None) -> list[dict]:
        return self.celdas.listar_con_ocupacion(
            TipoVehiculo(tipo) if tipo else None, EstadoCelda(estado) if estado else None
        )

    def crear_celda(self, codigo: str) -> Celda:
        codigo = (codigo or "").strip().upper()
        tipo = tipo_por_codigo_celda(codigo)
        if tipo is None:
            raise CodigoCeldaInvalido("El código debe tener el formato C-01 (carro) o M-01 (moto).")
        if self.celdas.buscar_por_codigo(codigo) is not None:
            raise CodigoCeldaInvalido(f"Ya existe una celda con el código {codigo}.")
        celda = Celda(None, codigo, tipo, EstadoCelda.DISPONIBLE)
        with self.conexion:
            celda.id = self.celdas.insertar(celda)
        return celda

    def cambiar_estado(self, id_celda: int, nuevo_estado: EstadoCelda) -> Celda:
        """RN-12: alterna entre DISPONIBLE y FUERA_DE_SERVICIO; una celda ocupada no se toca."""
        celda = self.obtener_celda(id_celda)
        if not celda.puede_cambiar_a(nuevo_estado):
            raise CambioEstadoCeldaInvalido(
                f"La celda {celda.codigo} está {celda.estado.value.replace('_', ' ').lower()} "
                f"y no puede pasar a {nuevo_estado.value.replace('_', ' ').lower()}."
            )
        with self.conexion:
            self.celdas.actualizar_estado(celda.id, nuevo_estado)
        celda.estado = nuevo_estado
        return celda

    def eliminar_celda(self, id_celda: int) -> Celda:
        """RN-13: solo se elimina una celda que nunca se ha usado; si no, se deja fuera de servicio."""
        celda = self.obtener_celda(id_celda)
        if celda.estado == EstadoCelda.OCUPADA or self.registros.contar_por_celda(celda.id):
            raise CeldaConHistorial(
                f"La celda {celda.codigo} tiene registros de parqueo. Póngala fuera de servicio en lugar de eliminarla."
            )
        with self.conexion:
            self.celdas.eliminar(celda.id)
        return celda

    def reubicar_vehiculo(self, placa: str, codigo_destino: str) -> ResultadoOperacion:
        """RN-14: mueve un vehículo que está dentro a otra celda disponible de su tipo."""
        placa = normalizar_placa(placa)
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        if vehiculo is None:
            raise VehiculoNoRegistrado(f"El vehículo {placa} no está registrado en el parqueadero.")
        registro = self.registros.activo_por_vehiculo(vehiculo.id)
        if registro is None:
            raise SinRegistroActivo(f"El vehículo {placa} no está dentro del parqueadero.")

        codigo_destino = (codigo_destino or "").strip().upper()
        destino = self.celdas.buscar_por_codigo(codigo_destino)
        if destino is None or not destino.puede_asignarse(vehiculo.tipo):
            raise CeldaNoDisponible(
                f"La celda {codigo_destino} no está disponible para un vehículo tipo {vehiculo.tipo.value}."
            )
        # RNF-03: liberar el origen, ocupar el destino y actualizar el registro, todo o nada.
        with self.conexion:
            self.registros.actualizar_celda(registro.id, destino.id)
            self.celdas.actualizar_estado(registro.celda_id, EstadoCelda.DISPONIBLE)
            self.celdas.actualizar_estado(destino.id, EstadoCelda.OCUPADA)
        registro.celda_id = destino.id
        destino.estado = EstadoCelda.OCUPADA
        return ResultadoOperacion(registro, vehiculo, destino)
