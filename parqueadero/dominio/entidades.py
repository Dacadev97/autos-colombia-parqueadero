"""Entidades y reglas del dominio: entrada y salida de vehículos (Iteración 1),
gestión de usuarios, vehículos y celdas (Iteración 2) y gestión de pagos (Iteración 3)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

PATRON_PLACA_CARRO = re.compile(r"^[A-Z]{3}\d{3}$")
PATRON_PLACA_MOTO = re.compile(r"^[A-Z]{3}\d{2}[A-Z]$")
PATRON_CODIGO_CELDA = re.compile(r"^([CM])-(\d{2})$")
PATRON_DOCUMENTO = re.compile(r"^\d{6,15}$")
PATRON_TELEFONO = re.compile(r"^\d{7,15}$")


class TipoVehiculo(str, Enum):
    CARRO = "CARRO"
    MOTO = "MOTO"


class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class RolOperador(str, Enum):
    OPERADOR = "OPERADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class EstadoCelda(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    OCUPADA = "OCUPADA"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


def normalizar_placa(placa: str) -> str:
    return (placa or "").replace("-", "").replace(" ", "").upper()


def placa_valida(placa: str) -> bool:
    return bool(PATRON_PLACA_CARRO.match(placa) or PATRON_PLACA_MOTO.match(placa))


def tipo_por_placa(placa: str) -> TipoVehiculo | None:
    """RN-09: el tipo del vehículo se deduce del formato de la placa."""
    if PATRON_PLACA_CARRO.match(placa):
        return TipoVehiculo.CARRO
    if PATRON_PLACA_MOTO.match(placa):
        return TipoVehiculo.MOTO
    return None


def tipo_por_codigo_celda(codigo: str) -> TipoVehiculo | None:
    """RN-11: el prefijo del código indica el tipo de la celda (C-xx carro, M-xx moto)."""
    coincidencia = PATRON_CODIGO_CELDA.match(codigo)
    if not coincidencia:
        return None
    return TipoVehiculo.CARRO if coincidencia.group(1) == "C" else TipoVehiculo.MOTO


def errores_datos_usuario(documento: str, nombre: str, telefono: str) -> list[str]:
    """RN-07: devuelve la lista de datos inválidos del usuario (vacía si todo es válido)."""
    errores = []
    if not PATRON_DOCUMENTO.match(documento):
        errores.append("el documento debe tener entre 6 y 15 dígitos")
    if not 3 <= len(nombre) <= 100:
        errores.append("el nombre debe tener entre 3 y 100 caracteres")
    if not PATRON_TELEFONO.match(telefono):
        errores.append("el teléfono debe tener entre 7 y 15 dígitos")
    return errores


@dataclass
class Usuario:
    id: int | None
    documento: str
    nombre: str
    telefono: str
    estado: EstadoUsuario

    def puede_ingresar(self) -> bool:
        return self.estado == EstadoUsuario.ACTIVO


@dataclass
class Vehiculo:
    id: int | None
    placa: str
    tipo: TipoVehiculo
    marca: str
    color: str
    usuario_id: int


@dataclass
class Celda:
    id: int | None
    codigo: str
    tipo: TipoVehiculo
    estado: EstadoCelda

    def puede_asignarse(self, tipo_vehiculo: TipoVehiculo) -> bool:
        return self.estado == EstadoCelda.DISPONIBLE and self.tipo == tipo_vehiculo

    def puede_cambiar_a(self, nuevo_estado: EstadoCelda) -> bool:
        """RN-12: el operador solo alterna entre DISPONIBLE y FUERA_DE_SERVICIO.
        OCUPADA la asignan únicamente la entrada, la salida y la reubicación."""
        permitidos = {
            EstadoCelda.FUERA_DE_SERVICIO: EstadoCelda.DISPONIBLE,
            EstadoCelda.DISPONIBLE: EstadoCelda.FUERA_DE_SERVICIO,
        }
        return permitidos.get(nuevo_estado) == self.estado


@dataclass
class Operador:
    id: int
    usuario: str
    nombre: str
    clave_hash: str
    rol: RolOperador = RolOperador.OPERADOR

    def es_administrador(self) -> bool:
        return self.rol == RolOperador.ADMINISTRADOR


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


# --- Iteración 3: gestión de pagos -----------------------------------------------------------------

PATRON_PERIODO = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9-]{4,30}$")
TARIFA_MINIMA, TARIFA_MAXIMA = 10_000, 2_000_000
MESES_ATRAS_PERMITIDOS, MESES_ADELANTE_PERMITIDOS = 12, 2


class MedioPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TARJETA = "TARJETA"

    def exige_referencia(self) -> bool:
        """RN-17: transferencia y tarjeta deben registrar la referencia de la transacción."""
        return self in (MedioPago.TRANSFERENCIA, MedioPago.TARJETA)


class EstadoPago(str, Enum):
    VIGENTE = "VIGENTE"
    ANULADO = "ANULADO"


def periodo_de(fecha: date) -> str:
    """Una mensualidad cubre un mes calendario, identificado como AAAA-MM."""
    return f"{fecha.year:04d}-{fecha.month:02d}"


def indice_periodo(periodo: str) -> int | None:
    """Número de meses desde el año 0; permite comparar y restar periodos. None si el formato es inválido."""
    coincidencia = PATRON_PERIODO.match(periodo or "")
    if not coincidencia:
        return None
    return int(coincidencia.group(1)) * 12 + int(coincidencia.group(2)) - 1


def periodo_en_rango(periodo: str, hoy: date) -> bool:
    """RN-16: se aceptan pagos de hasta 12 meses atrasados y hasta 2 meses por adelantado."""
    indice = indice_periodo(periodo)
    if indice is None:
        return False
    actual = indice_periodo(periodo_de(hoy))
    return actual - MESES_ATRAS_PERMITIDOS <= indice <= actual + MESES_ADELANTE_PERMITIDOS


def tarifa_valida(valor: int) -> bool:
    """RN-15: la tarifa mensual es un entero en pesos entre 10 000 y 2 000 000."""
    return isinstance(valor, int) and TARIFA_MINIMA <= valor <= TARIFA_MAXIMA


@dataclass
class Tarifa:
    tipo: TipoVehiculo
    valor_mensual: int


@dataclass
class Pago:
    id: int | None
    vehiculo_id: int
    periodo: str
    valor: int
    medio: MedioPago
    referencia: str | None
    fecha_pago: datetime
    operador_id: int
    estado: EstadoPago = EstadoPago.VIGENTE
    motivo_anulacion: str | None = None
    fecha_anulacion: datetime | None = None
    operador_anulacion_id: int | None = None

    @property
    def numero_recibo(self) -> str:
        """El recibo toma el consecutivo del pago: REC-000001, REC-000002, …"""
        return f"REC-{self.id:06d}" if self.id else "REC-PENDIENTE"

    def esta_vigente(self) -> bool:
        return self.estado == EstadoPago.VIGENTE

    def anular(self, operador_id: int, fecha: datetime, motivo: str) -> None:
        """RN-20: un pago nunca se borra; se anula con motivo y queda en el historial."""
        if not self.esta_vigente():
            raise ValueError("El pago ya está anulado.")
        self.estado = EstadoPago.ANULADO
        self.operador_anulacion_id = operador_id
        self.fecha_anulacion = fecha
        self.motivo_anulacion = motivo
