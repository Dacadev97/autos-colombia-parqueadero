"""Entidades y reglas del dominio para la gestión de entrada y salida de vehículos."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

PATRON_PLACA_CARRO = re.compile(r"^[A-Z]{3}\d{3}$")
PATRON_PLACA_MOTO = re.compile(r"^[A-Z]{3}\d{2}[A-Z]$")


class TipoVehiculo(str, Enum):
    CARRO = "CARRO"
    MOTO = "MOTO"


class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class EstadoCelda(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    OCUPADA = "OCUPADA"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


def normalizar_placa(placa: str) -> str:
    return (placa or "").replace("-", "").replace(" ", "").upper()


def placa_valida(placa: str) -> bool:
    return bool(PATRON_PLACA_CARRO.match(placa) or PATRON_PLACA_MOTO.match(placa))


@dataclass
class Usuario:
    id: int
    documento: str
    nombre: str
    telefono: str
    estado: EstadoUsuario

    def puede_ingresar(self) -> bool:
        return self.estado == EstadoUsuario.ACTIVO


@dataclass
class Vehiculo:
    id: int
    placa: str
    tipo: TipoVehiculo
    marca: str
    color: str
    usuario_id: int


@dataclass
class Celda:
    id: int
    codigo: str
    tipo: TipoVehiculo
    estado: EstadoCelda

    def puede_asignarse(self, tipo_vehiculo: TipoVehiculo) -> bool:
        return self.estado == EstadoCelda.DISPONIBLE and self.tipo == tipo_vehiculo


@dataclass
class Operador:
    id: int
    usuario: str
    nombre: str
    clave_hash: str


@dataclass
class RegistroParqueo:
    id: int | None
    vehiculo_id: int
    celda_id: int
    operador_entrada_id: int
    fecha_entrada: datetime
    observacion_entrada: str | None = None
    operador_salida_id: int | None = None
    fecha_salida: datetime | None = None
    observacion_salida: str | None = None

    def esta_activo(self) -> bool:
        return self.fecha_salida is None

    def registrar_salida(self, operador_id: int, fecha: datetime, observacion: str | None) -> None:
        if not self.esta_activo():
            raise ValueError("El registro ya tiene una salida registrada.")
        if fecha < self.fecha_entrada:
            raise ValueError("La fecha de salida no puede ser anterior a la de entrada.")
        self.operador_salida_id = operador_id
        self.fecha_salida = fecha
        self.observacion_salida = observacion or None
