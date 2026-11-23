"""Violaciones de reglas de negocio. Cada una lleva el mensaje que verá el operador."""


class ReglaNegocioError(Exception):
    codigo = "RN"

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class PlacaInvalida(ReglaNegocioError):
    codigo = "RN-00"


class VehiculoNoRegistrado(ReglaNegocioError):
    codigo = "RN-01"


class UsuarioInactivo(ReglaNegocioError):
    codigo = "RN-01"


class VehiculoYaDentro(ReglaNegocioError):
    codigo = "RN-02"


class CeldaNoDisponible(ReglaNegocioError):
    codigo = "RN-03"


class SinCeldasDisponibles(ReglaNegocioError):
    codigo = "RN-03"


class SinRegistroActivo(ReglaNegocioError):
    codigo = "RN-05"


# Iteración 2: gestión de usuarios, vehículos y celdas
class DatosUsuarioInvalidos(ReglaNegocioError):
    codigo = "RN-07"


class DocumentoDuplicado(ReglaNegocioError):
    codigo = "RN-07"


class UsuarioNoEncontrado(ReglaNegocioError):
    codigo = "RN-07"


class EstadoUsuarioSinCambio(ReglaNegocioError):
    codigo = "RN-08"


class DatosVehiculoInvalidos(ReglaNegocioError):
    codigo = "RN-09"


class PlacaDuplicada(ReglaNegocioError):
    codigo = "RN-09"


class VehiculoNoEncontrado(ReglaNegocioError):
    codigo = "RN-09"


class VehiculoConHistorial(ReglaNegocioError):
    codigo = "RN-10"


class CodigoCeldaInvalido(ReglaNegocioError):
    codigo = "RN-11"


class CeldaNoEncontrada(ReglaNegocioError):
    codigo = "RN-11"


class CambioEstadoCeldaInvalido(ReglaNegocioError):
    codigo = "RN-12"


class CeldaConHistorial(ReglaNegocioError):
    codigo = "RN-13"


# Iteración 3: gestión de pagos
class TarifaInvalida(ReglaNegocioError):
    codigo = "RN-15"


class TarifaNoConfigurada(ReglaNegocioError):
    codigo = "RN-15"


class PeriodoInvalido(ReglaNegocioError):
    codigo = "RN-16"


class PeriodoYaPagado(ReglaNegocioError):
    codigo = "RN-16"


class MedioPagoInvalido(ReglaNegocioError):
    codigo = "RN-17"


class ReferenciaPagoInvalida(ReglaNegocioError):
    codigo = "RN-17"


class TitularInactivoNoPaga(ReglaNegocioError):
    codigo = "RN-18"


class MensualidadVencida(ReglaNegocioError):
    codigo = "RN-19"


class PagoNoEncontrado(ReglaNegocioError):
    codigo = "RN-20"


class AnulacionInvalida(ReglaNegocioError):
    codigo = "RN-20"
