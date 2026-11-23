"""Casos de uso de la Iteración 3: gestión de pagos de la mensualidad y de las tarifas."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from parqueadero.dominio.entidades import (
    EstadoPago,
    MedioPago,
    Pago,
    PATRON_REFERENCIA,
    Tarifa,
    TipoVehiculo,
    Usuario,
    Vehiculo,
    normalizar_placa,
    periodo_de,
    periodo_en_rango,
    placa_valida,
    tarifa_valida,
)
from parqueadero.dominio.excepciones import (
    AnulacionInvalida,
    MedioPagoInvalido,
    PagoNoEncontrado,
    PeriodoInvalido,
    PeriodoYaPagado,
    PlacaInvalida,
    ReferenciaPagoInvalida,
    TarifaInvalida,
    TarifaNoConfigurada,
    TitularInactivoNoPaga,
    VehiculoNoRegistrado,
)
from parqueadero.persistencia.repositorios import (
    RepositorioPagos,
    RepositorioTarifas,
    RepositorioUsuarios,
    RepositorioVehiculos,
)

LONGITUD_MOTIVO = (5, 200)


@dataclass
class ResultadoPago:
    pago: Pago
    vehiculo: Vehiculo
    usuario: Usuario


@dataclass
class EstadoCuenta:
    vehiculo: Vehiculo
    periodo_actual: str
    al_dia: bool
    periodos_pagados: list[str]
    ultimo_periodo: str | None


class ServicioPagos:
    def __init__(self, conexion: sqlite3.Connection, reloj: Callable[[], datetime] = datetime.now):
        self.conexion = conexion
        self.reloj = reloj
        self.pagos = RepositorioPagos(conexion)
        self.tarifas = RepositorioTarifas(conexion)
        self.usuarios = RepositorioUsuarios(conexion)
        self.vehiculos = RepositorioVehiculos(conexion)

    def _ahora(self) -> datetime:
        return self.reloj().replace(microsecond=0)

    def _vehiculo(self, placa: str) -> Vehiculo:
        placa = normalizar_placa(placa)
        if not placa_valida(placa):
            raise PlacaInvalida("La placa no tiene un formato válido (ABC123 para carro o ABC12D para moto).")
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        if vehiculo is None:
            raise VehiculoNoRegistrado(f"El vehículo {placa} no está registrado en el parqueadero.")
        return vehiculo

    # --- Tarifas (RN-15) --------------------------------------------------------------------------

    def listar_tarifas(self) -> list[Tarifa]:
        return self.tarifas.listar()

    def actualizar_tarifa(self, tipo: str, valor: str | int) -> Tarifa:
        try:
            tipo_vehiculo = TipoVehiculo(str(tipo).upper())
            valor_entero = int(str(valor).replace(".", "").replace(" ", ""))
        except ValueError:
            raise TarifaInvalida("La tarifa debe indicar un tipo (CARRO o MOTO) y un valor entero en pesos.")
        if not tarifa_valida(valor_entero):
            raise TarifaInvalida("La tarifa mensual debe estar entre $10.000 y $2.000.000.")
        tarifa = Tarifa(tipo_vehiculo, valor_entero)
        with self.conexion:
            self.tarifas.guardar(tarifa)
        return tarifa

    # --- Pagos (RN-16, RN-17, RN-18) --------------------------------------------------------------

    def registrar_pago(self, placa: str, periodo: str, medio: str, operador_id: int,
                       referencia: str | None = None) -> ResultadoPago:
        vehiculo = self._vehiculo(placa)
        usuario = self.usuarios.buscar_por_id(vehiculo.usuario_id)
        if usuario is None or not usuario.puede_ingresar():
            raise TitularInactivoNoPaga(
                f"El titular del vehículo {vehiculo.placa} está inactivo; reactívelo antes de registrar el pago."
            )

        periodo = (periodo or "").strip()
        hoy = self._ahora()
        if not periodo_en_rango(periodo, hoy.date()):
            raise PeriodoInvalido(
                "El periodo debe tener el formato AAAA-MM y estar entre 12 meses atrás y 2 meses adelante "
                f"de {periodo_de(hoy.date())}."
            )
        if self.pagos.vigente(vehiculo.id, periodo) is not None:
            raise PeriodoYaPagado(f"El vehículo {vehiculo.placa} ya tiene pagada la mensualidad de {periodo}.")

        try:
            medio_pago = MedioPago((medio or "").upper())
        except ValueError:
            raise MedioPagoInvalido("El medio de pago debe ser EFECTIVO, TRANSFERENCIA o TARJETA.")
        referencia = (referencia or "").strip() or None
        if medio_pago.exige_referencia():
            if not referencia or not PATRON_REFERENCIA.match(referencia):
                raise ReferenciaPagoInvalida(
                    f"El pago por {medio_pago.value.lower()} exige una referencia de 4 a 30 letras, números o guiones."
                )
        else:
            referencia = None

        tarifa = self.tarifas.obtener(vehiculo.tipo)
        if tarifa is None:
            raise TarifaNoConfigurada(f"No hay una tarifa mensual configurada para {vehiculo.tipo.value}.")

        # El valor se copia de la tarifa vigente: cambiar la tarifa después no altera pagos ya hechos.
        pago = Pago(None, vehiculo.id, periodo, tarifa.valor_mensual, medio_pago, referencia, hoy, operador_id)
        # RNF-15: el pago y su consecutivo se guardan en una sola transacción.
        with self.conexion:
            pago.id = self.pagos.insertar(pago)
        return ResultadoPago(pago, vehiculo, usuario)

    def obtener_pago(self, id_pago: int) -> ResultadoPago:
        pago = self.pagos.buscar_por_id(id_pago)
        if pago is None:
            raise PagoNoEncontrado("El pago solicitado no existe.")
        vehiculo = self.vehiculos.buscar_por_id(pago.vehiculo_id)
        return ResultadoPago(pago, vehiculo, self.usuarios.buscar_por_id(vehiculo.usuario_id))

    def anular_pago(self, id_pago: int, motivo: str, operador_id: int) -> Pago:
        """RN-20: el pago no se borra; queda ANULADO con motivo, fecha y operador, y deja libre el periodo."""
        pago = self.obtener_pago(id_pago).pago
        motivo = " ".join((motivo or "").split())
        if not LONGITUD_MOTIVO[0] <= len(motivo) <= LONGITUD_MOTIVO[1]:
            raise AnulacionInvalida("El motivo de la anulación debe tener entre 5 y 200 caracteres.")
        if not pago.esta_vigente():
            raise AnulacionInvalida(f"El recibo {pago.numero_recibo} ya está anulado.")
        pago.anular(operador_id, self._ahora(), motivo)
        with self.conexion:
            self.pagos.actualizar_anulacion(pago)
        return pago

    # --- Consultas (RF-22, RF-23) -----------------------------------------------------------------

    def listar_pagos(self, placa: str | None = None, periodo: str | None = None,
                     estado: str | None = None) -> list[dict]:
        return self.pagos.listar_detalle(
            normalizar_placa(placa) or None, (periodo or "").strip() or None, EstadoPago(estado) if estado else None
        )

    def recaudo(self, periodo: str | None = None) -> int:
        return self.pagos.recaudo((periodo or "").strip() or None)

    def periodo_actual(self) -> str:
        return periodo_de(self._ahora().date())

    def estado_cuenta(self, vehiculo: Vehiculo) -> EstadoCuenta:
        actual = self.periodo_actual()
        pagados = self.pagos.periodos_pagados(vehiculo.id)
        return EstadoCuenta(vehiculo, actual, actual in pagados, pagados, pagados[-1] if pagados else None)

    def esta_al_dia(self, id_vehiculo: int, fecha: datetime) -> bool:
        """RN-19: el vehículo tiene pagada la mensualidad del mes de la fecha indicada."""
        return self.pagos.vigente(id_vehiculo, periodo_de(fecha.date())) is not None
