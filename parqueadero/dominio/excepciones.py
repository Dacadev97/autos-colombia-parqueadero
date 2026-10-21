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
