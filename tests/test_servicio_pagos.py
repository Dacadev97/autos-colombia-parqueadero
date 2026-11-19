"""Plan de pruebas de la Iteración 3 (gestión de pagos): CP-25 a CP-36.

Cada prueba verifica el dato guardado en la base, no solo el mensaje que ve el operador.
"""
from datetime import datetime

import pytest

from parqueadero.aplicacion.servicio_pagos import ServicioPagos
from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.aplicacion.servicio_usuarios import ServicioUsuarios
from parqueadero.dominio.entidades import EstadoPago, EstadoUsuario
from parqueadero.dominio.excepciones import (
    AnulacionInvalida,
    MedioPagoInvalido,
    MensualidadVencida,
    PeriodoInvalido,
    PeriodoYaPagado,
    ReferenciaPagoInvalida,
    TarifaInvalida,
    TitularInactivoNoPaga,
    VehiculoNoRegistrado,
)

OPERADOR, ADMIN = 1, 2


class RelojFijo:
    def __init__(self, ahora: datetime):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora


@pytest.fixture
def reloj():
    return RelojFijo(datetime(2026, 11, 19, 10, 0, 0))


@pytest.fixture
def pagos(conexion, reloj):
    return ServicioPagos(conexion, reloj)


def _fila_pago(conexion, id_pago):
    return conexion.execute("SELECT * FROM pago WHERE id_pago = ?", (id_pago,)).fetchone()


# CP-25 (HU-16, RN-15): el pago toma el valor de la tarifa vigente y genera un recibo consecutivo.
def test_cp25_registra_pago_con_valor_de_la_tarifa_y_recibo(pagos, conexion):
    servicio_usuarios = ServicioUsuarios(conexion)
    servicio_usuarios.registrar_vehiculo(1, "DEF456", "Kia", "Azul")
    resultado = pagos.registrar_pago("def-456", "2026-11", "efectivo", OPERADOR)

    fila = _fila_pago(conexion, resultado.pago.id)
    assert (fila["periodo"], fila["valor"], fila["medio"], fila["estado"]) == ("2026-11", 180_000, "EFECTIVO", "VIGENTE")
    assert fila["referencia"] is None and fila["fecha_pago"] == "2026-11-19 10:00:00"
    assert resultado.pago.numero_recibo == f"REC-{resultado.pago.id:06d}"


# CP-26 (RN-16): no se paga dos veces el mismo mes; la base lo garantiza también.
def test_cp26_rechaza_mes_ya_pagado_sin_crear_registro(pagos, conexion):
    antes = conexion.execute("SELECT COUNT(*) FROM pago").fetchone()[0]
    with pytest.raises(PeriodoYaPagado):
        pagos.registrar_pago("ABC123", "2026-11", "EFECTIVO", OPERADOR)
    assert conexion.execute("SELECT COUNT(*) FROM pago").fetchone()[0] == antes


# CP-27 (RN-16): el periodo debe ser AAAA-MM, hasta 12 meses atrás y 2 adelante.
@pytest.mark.parametrize("periodo", ["2026-13", "11-2026", "2025-10", "2027-02", ""])
def test_cp27_rechaza_periodos_fuera_de_formato_o_de_rango(pagos, periodo):
    with pytest.raises(PeriodoInvalido):
        pagos.registrar_pago("ABC123", periodo, "EFECTIVO", OPERADOR)


def test_cp27b_acepta_pago_adelantado_dentro_del_rango(pagos, conexion):
    resultado = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR)
    assert _fila_pago(conexion, resultado.pago.id)["periodo"] == "2027-01"


# CP-28 (RN-17): transferencia y tarjeta exigen referencia; el medio debe existir.
def test_cp28_valida_medio_y_referencia(pagos, conexion):
    with pytest.raises(ReferenciaPagoInvalida):
        pagos.registrar_pago("ABC123", "2027-01", "TRANSFERENCIA", OPERADOR, "")
    with pytest.raises(ReferenciaPagoInvalida):
        pagos.registrar_pago("ABC123", "2027-01", "TARJETA", OPERADOR, "a b")
    with pytest.raises(MedioPagoInvalido):
        pagos.registrar_pago("ABC123", "2027-01", "CHEQUE", OPERADOR)
    resultado = pagos.registrar_pago("ABC123", "2027-01", "TARJETA", OPERADOR, "VOUCHER-8841")
    assert _fila_pago(conexion, resultado.pago.id)["referencia"] == "VOUCHER-8841"


# CP-29 (RN-18): el titular inactivo no puede pagar; un vehículo inexistente tampoco.
def test_cp29_rechaza_titular_inactivo_y_vehiculo_inexistente(pagos):
    with pytest.raises(TitularInactivoNoPaga):
        pagos.registrar_pago("JKL321", "2026-11", "EFECTIVO", OPERADOR)
    with pytest.raises(VehiculoNoRegistrado):
        pagos.registrar_pago("ZZZ999", "2026-11", "EFECTIVO", OPERADOR)


# CP-30 (HU-21, RN-19): sin la mensualidad del mes no hay ingreso; al pagar, entra.
def test_cp30_entrada_exige_mensualidad_del_mes(conexion, reloj, pagos):
    ServicioUsuarios(conexion).registrar_vehiculo(1, "DEF456", "Kia", "Azul")
    parqueo = ServicioParqueo(conexion, reloj)
    with pytest.raises(MensualidadVencida):
        parqueo.registrar_entrada("DEF456", OPERADOR)
    assert conexion.execute("SELECT COUNT(*) FROM registro_parqueo").fetchone()[0] == 0

    pagos.registrar_pago("DEF456", "2026-11", "EFECTIVO", OPERADOR)
    resultado = parqueo.registrar_entrada("DEF456", OPERADOR)
    assert conexion.execute("SELECT estado FROM celda WHERE id_celda = ?", (resultado.celda.id,)).fetchone()[0] == "OCUPADA"


def test_cp30b_el_mes_siguiente_sin_pagar_bloquea_la_entrada(conexion):
    parqueo = ServicioParqueo(conexion, RelojFijo(datetime(2027, 1, 5, 7, 0, 0)))
    with pytest.raises(MensualidadVencida):
        parqueo.registrar_entrada("ABC123", OPERADOR)


# CP-31 (HU-19, RN-20): anular no borra; deja motivo, fecha y operador, y libera el mes.
def test_cp31_anula_pago_y_el_mes_vuelve_a_quedar_pendiente(pagos, conexion):
    pago = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR).pago
    pagos.anular_pago(pago.id, "Se cobró a la placa equivocada", ADMIN)

    fila = _fila_pago(conexion, pago.id)
    assert (fila["estado"], fila["motivo_anulacion"], fila["id_operador_anulacion"]) == (
        "ANULADO", "Se cobró a la placa equivocada", ADMIN)
    assert fila["fecha_anulacion"] == "2026-11-19 10:00:00"
    nuevo = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR).pago
    assert nuevo.id != pago.id


def test_cp31b_rechaza_anulacion_repetida_o_sin_motivo(pagos):
    pago = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR).pago
    with pytest.raises(AnulacionInvalida):
        pagos.anular_pago(pago.id, "no", ADMIN)
    pagos.anular_pago(pago.id, "Error de digitación", ADMIN)
    with pytest.raises(AnulacionInvalida):
        pagos.anular_pago(pago.id, "Otra vez", ADMIN)


# CP-32 (HU-17): consulta por placa, mes y estado; el recaudo excluye los anulados.
def test_cp32_consulta_pagos_y_recaudo_sin_anulados(pagos):
    assert pagos.recaudo("2026-11") == 180_000 + 180_000 + 70_000
    pago = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR).pago
    pagos.anular_pago(pago.id, "Pago duplicado", ADMIN)
    assert pagos.recaudo("2027-01") == 0
    assert [p["periodo"] for p in pagos.listar_pagos(placa="abc123", estado="ANULADO")] == ["2027-01"]
    assert {p["placa"] for p in pagos.listar_pagos(periodo="2026-11")} == {"ABC123", "XYZ789", "FGH45K"}


# CP-33 (HU-18): estado de cuenta del vehículo.
def test_cp33_estado_de_cuenta(pagos, conexion):
    servicio_usuarios = ServicioUsuarios(conexion)
    al_dia = pagos.estado_cuenta(servicio_usuarios.obtener_vehiculo(1))
    assert (al_dia.al_dia, al_dia.periodo_actual, al_dia.ultimo_periodo) == (True, "2026-11", "2026-12")
    nuevo = servicio_usuarios.registrar_vehiculo(1, "DEF456", "Kia", "Azul")
    pendiente = pagos.estado_cuenta(nuevo)
    assert (pendiente.al_dia, pendiente.ultimo_periodo) == (False, None)


# CP-34 (HU-20, RN-15): la tarifa se valida y un cambio no altera pagos ya emitidos.
def test_cp34_actualiza_tarifa_sin_alterar_pagos_anteriores(pagos, conexion):
    with pytest.raises(TarifaInvalida):
        pagos.actualizar_tarifa("CARRO", "5000")
    with pytest.raises(TarifaInvalida):
        pagos.actualizar_tarifa("BUS", "100000")
    pagos.actualizar_tarifa("CARRO", "200.000")
    assert conexion.execute("SELECT valor_mensual FROM tarifa WHERE tipo = 'CARRO'").fetchone()[0] == 200_000
    assert conexion.execute("SELECT valor FROM pago WHERE periodo = '2026-11' AND id_vehiculo = 1").fetchone()[0] == 180_000
    nuevo = pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR).pago
    assert _fila_pago(conexion, nuevo.id)["valor"] == 200_000


# CP-35 (RNF-15): si la escritura falla, no queda un pago a medias.
def test_cp35_pago_atomico_ante_falla_de_la_base(pagos, conexion, monkeypatch):
    antes = conexion.execute("SELECT COUNT(*) FROM pago").fetchone()[0]

    def falla(_pago):
        conexion.execute("INSERT INTO pago (id_vehiculo, periodo, valor, medio, fecha_pago, id_operador) "
                         "VALUES (1, '2027-01', 1, 'EFECTIVO', '2026-11-19 10:00:00', 1)")
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(pagos.pagos, "insertar", falla)
    with pytest.raises(RuntimeError):
        pagos.registrar_pago("ABC123", "2027-01", "EFECTIVO", OPERADOR)
    assert conexion.execute("SELECT COUNT(*) FROM pago").fetchone()[0] == antes


# CP-36 (RN-18 + RN-08): al reactivar al titular, paga y vuelve a ingresar.
def test_cp36_reactivar_pagar_e_ingresar(conexion, reloj, pagos):
    ServicioUsuarios(conexion).cambiar_estado(3, EstadoUsuario.ACTIVO)
    pago = pagos.registrar_pago("JKL321", "2026-11", "TRANSFERENCIA", OPERADOR, "TRF-55021").pago
    assert pago.estado == EstadoPago.VIGENTE
    assert ServicioParqueo(conexion, reloj).registrar_entrada("JKL321", OPERADOR).celda.codigo == "C-01"
