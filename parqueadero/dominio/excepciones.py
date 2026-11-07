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
