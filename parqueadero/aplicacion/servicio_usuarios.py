"""Casos de uso de la Iteración 2: gestión de usuarios (clientes mensuales) y de sus vehículos."""

import sqlite3

from parqueadero.dominio.entidades import (
    EstadoUsuario,
    Usuario,
    Vehiculo,
    errores_datos_usuario,
    normalizar_placa,
    tipo_por_placa,
)
from parqueadero.dominio.excepciones import (
    DatosUsuarioInvalidos,
    DatosVehiculoInvalidos,
    DocumentoDuplicado,
    EstadoUsuarioSinCambio,
    PlacaDuplicada,
    PlacaInvalida,
    UsuarioNoEncontrado,
    VehiculoConHistorial,
    VehiculoNoEncontrado,
)
from parqueadero.persistencia.repositorios import (
    RepositorioRegistros,
    RepositorioUsuarios,
    RepositorioVehiculos,
)


def _limpiar(texto: str | None) -> str:
    return " ".join((texto or "").split())


class ServicioUsuarios:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion
        self.usuarios = RepositorioUsuarios(conexion)
        self.vehiculos = RepositorioVehiculos(conexion)
        self.registros = RepositorioRegistros(conexion)

    # --- Usuarios -----------------------------------------------------------------------------

    def obtener_usuario(self, id_usuario: int) -> Usuario:
        usuario = self.usuarios.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNoEncontrado("El usuario solicitado no existe.")
        return usuario

    def listar_usuarios(self, texto: str | None = None, estado: str | None = None) -> list[dict]:
        return self.usuarios.listar(_limpiar(texto) or None, EstadoUsuario(estado) if estado else None)

    @staticmethod
    def _validar(documento: str, nombre: str, telefono: str) -> None:
        errores = errores_datos_usuario(documento, nombre, telefono)
        if errores:
            raise DatosUsuarioInvalidos("Datos inválidos: " + "; ".join(errores) + ".")

    def registrar_usuario(self, documento: str, nombre: str, telefono: str) -> Usuario:
        documento, nombre, telefono = _limpiar(documento), _limpiar(nombre), _limpiar(telefono)
        self._validar(documento, nombre, telefono)
        if self.usuarios.buscar_por_documento(documento) is not None:
            raise DocumentoDuplicado(f"Ya existe un usuario con el documento {documento}.")
        usuario = Usuario(None, documento, nombre, telefono, EstadoUsuario.ACTIVO)
        with self.conexion:
            usuario.id = self.usuarios.insertar(usuario)
        return usuario

    def actualizar_usuario(self, id_usuario: int, nombre: str, telefono: str) -> Usuario:
        usuario = self.obtener_usuario(id_usuario)
        nombre, telefono = _limpiar(nombre), _limpiar(telefono)
        self._validar(usuario.documento, nombre, telefono)
        usuario.nombre, usuario.telefono = nombre, telefono
        with self.conexion:
            self.usuarios.actualizar(usuario)
        return usuario

    def cambiar_estado(self, id_usuario: int, estado: EstadoUsuario) -> Usuario:
        """RN-08: baja lógica. El usuario no se borra para conservar el historial."""
        usuario = self.obtener_usuario(id_usuario)
        if usuario.estado == estado:
            raise EstadoUsuarioSinCambio(f"El usuario ya está {estado.value.lower()}.")
        usuario.estado = estado
        with self.conexion:
            self.usuarios.actualizar(usuario)
        return usuario

    # --- Vehículos ----------------------------------------------------------------------------

    def vehiculos_de(self, id_usuario: int) -> list[dict]:
        return self.vehiculos.listar_por_usuario(id_usuario)

    def obtener_vehiculo(self, id_vehiculo: int) -> Vehiculo:
        vehiculo = self.vehiculos.buscar_por_id(id_vehiculo)
        if vehiculo is None:
            raise VehiculoNoEncontrado("El vehículo solicitado no existe.")
        return vehiculo

    @staticmethod
    def _validar_vehiculo(marca: str, color: str) -> None:
        if not 2 <= len(marca) <= 30 or not 3 <= len(color) <= 20:
            raise DatosVehiculoInvalidos(
                "Datos inválidos: la marca debe tener entre 2 y 30 caracteres y el color entre 3 y 20."
            )

    def registrar_vehiculo(self, id_usuario: int, placa: str, marca: str, color: str) -> Vehiculo:
        usuario = self.obtener_usuario(id_usuario)
        placa, marca, color = normalizar_placa(placa), _limpiar(marca), _limpiar(color)
        tipo = tipo_por_placa(placa)
        if tipo is None:
            raise PlacaInvalida("La placa no tiene un formato válido (ABC123 para carro o ABC12D para moto).")
        self._validar_vehiculo(marca, color)
        if self.vehiculos.buscar_por_placa(placa) is not None:
            raise PlacaDuplicada(f"La placa {placa} ya está registrada en el parqueadero.")
        vehiculo = Vehiculo(None, placa, tipo, marca, color, usuario.id)
        with self.conexion:
            vehiculo.id = self.vehiculos.insertar(vehiculo)
        return vehiculo

    def actualizar_vehiculo(self, id_vehiculo: int, marca: str, color: str) -> Vehiculo:
        vehiculo = self.obtener_vehiculo(id_vehiculo)
        marca, color = _limpiar(marca), _limpiar(color)
        self._validar_vehiculo(marca, color)
        vehiculo.marca, vehiculo.color = marca, color
        with self.conexion:
            self.vehiculos.actualizar(vehiculo)
        return vehiculo

    def eliminar_vehiculo(self, id_vehiculo: int) -> Vehiculo:
        """RN-10: solo se elimina un vehículo sin registros de parqueo (ni dentro ni con historial)."""
        vehiculo = self.obtener_vehiculo(id_vehiculo)
        if self.registros.contar_por_vehiculo(vehiculo.id):
            raise VehiculoConHistorial(
                f"El vehículo {vehiculo.placa} tiene registros de parqueo y no puede eliminarse."
            )
        with self.conexion:
            self.vehiculos.eliminar(vehiculo.id)
        return vehiculo
