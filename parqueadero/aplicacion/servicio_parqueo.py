"""Casos de uso de la Iteración 1: registrar entrada, registrar salida y consultas."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from parqueadero.dominio.entidades import (
    Celda,
    EstadoCelda,
    RegistroParqueo,
    Vehiculo,
    normalizar_placa,
    placa_valida,
)
from parqueadero.dominio.excepciones import (
    CeldaNoDisponible,
    PlacaInvalida,
    SinCeldasDisponibles,
    SinRegistroActivo,
    UsuarioInactivo,
    VehiculoNoRegistrado,
    VehiculoYaDentro,
)
from parqueadero.persistencia.repositorios import (
    RepositorioCeldas,
    RepositorioRegistros,
    RepositorioUsuarios,
    RepositorioVehiculos,
)

LONGITUD_MAXIMA_OBSERVACION = 255


@dataclass
class ResultadoOperacion:
    registro: RegistroParqueo
    vehiculo: Vehiculo
    celda: Celda


class ServicioParqueo:
    def __init__(self, conexion: sqlite3.Connection, reloj: Callable[[], datetime] = datetime.now):
        self.conexion = conexion
        self.reloj = reloj
        self.usuarios = RepositorioUsuarios(conexion)
        self.vehiculos = RepositorioVehiculos(conexion)
        self.celdas = RepositorioCeldas(conexion)
        self.registros = RepositorioRegistros(conexion)

    def _ahora(self) -> datetime:
        return self.reloj().replace(microsecond=0)

    def _vehiculo_registrado(self, placa: str) -> Vehiculo:
        placa = normalizar_placa(placa)
        if not placa_valida(placa):
            raise PlacaInvalida("La placa no tiene un formato válido (ABC123 para carro o ABC12D para moto).")
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        if vehiculo is None:
            raise VehiculoNoRegistrado(f"El vehículo {placa} no está registrado en el parqueadero.")
        return vehiculo

    @staticmethod
    def _limpiar_observacion(observacion: str | None) -> str | None:
        texto = (observacion or "").strip()
        return texto[:LONGITUD_MAXIMA_OBSERVACION] or None

    def registrar_entrada(self, placa: str, operador_id: int, codigo_celda: str | None = None,
                          observacion: str | None = None) -> ResultadoOperacion:
        vehiculo = self._vehiculo_registrado(placa)

        usuario = self.usuarios.buscar_por_id(vehiculo.usuario_id)
        if usuario is None or not usuario.puede_ingresar():
            raise UsuarioInactivo(f"El usuario titular del vehículo {vehiculo.placa} está inactivo.")

        if self.registros.activo_por_vehiculo(vehiculo.id) is not None:
            raise VehiculoYaDentro(f"El vehículo {vehiculo.placa} ya tiene una entrada activa.")

        if codigo_celda:
            celda = self.celdas.buscar_por_codigo(codigo_celda.strip().upper())
            if celda is None or not celda.puede_asignarse(vehiculo.tipo):
                raise CeldaNoDisponible(
                    f"La celda {codigo_celda.upper()} no está disponible para un vehículo tipo {vehiculo.tipo.value}."
                )
        else:
            celda = self.celdas.primera_disponible(vehiculo.tipo)
            if celda is None:
                raise SinCeldasDisponibles(f"No hay celdas disponibles para vehículos tipo {vehiculo.tipo.value}.")

        registro = RegistroParqueo(
            id=None,
            vehiculo_id=vehiculo.id,
            celda_id=celda.id,
            operador_entrada_id=operador_id,
            fecha_entrada=self._ahora(),
            observacion_entrada=self._limpiar_observacion(observacion),
        )
        # RNF-03: el registro y el cambio de estado de la celda se guardan juntos o no se guarda nada.
        with self.conexion:
            registro.id = self.registros.insertar(registro)
            self.celdas.actualizar_estado(celda.id, EstadoCelda.OCUPADA)
        celda.estado = EstadoCelda.OCUPADA
        return ResultadoOperacion(registro, vehiculo, celda)

    def registrar_salida(self, placa: str, operador_id: int,
                         observacion: str | None = None) -> ResultadoOperacion:
        vehiculo = self._vehiculo_registrado(placa)

        registro = self.registros.activo_por_vehiculo(vehiculo.id)
        if registro is None:
            raise SinRegistroActivo(f"El vehículo {vehiculo.placa} no tiene una entrada activa para registrar su salida.")

        registro.registrar_salida(operador_id, self._ahora(), self._limpiar_observacion(observacion))
        celda = self.celdas.buscar_por_id(registro.celda_id)
        with self.conexion:
            self.registros.actualizar_salida(registro)
            self.celdas.actualizar_estado(celda.id, EstadoCelda.DISPONIBLE)
        celda.estado = EstadoCelda.DISPONIBLE
        return ResultadoOperacion(registro, vehiculo, celda)

    def vehiculos_dentro(self) -> list[dict]:
        return self.registros.listar_detalle(solo_activos=True)

    def historial(self, placa: str | None = None, desde: str | None = None,
                  hasta: str | None = None) -> list[dict]:
        return self.registros.listar_detalle(
            solo_activos=False, placa=normalizar_placa(placa) or None, desde=desde or None, hasta=hasta or None
        )

    def resumen_celdas(self) -> dict:
        resumen: dict = {}
        for celda in self.celdas.listar():
            por_tipo = resumen.setdefault(celda.tipo.value, {e.value: 0 for e in EstadoCelda})
            por_tipo[celda.estado.value] += 1
        return resumen
