import sqlite3

from werkzeug.security import check_password_hash

from parqueadero.dominio.entidades import Operador
from parqueadero.persistencia.repositorios import RepositorioOperadores


class ServicioAutenticacion:
    def __init__(self, conexion: sqlite3.Connection):
        self.operadores = RepositorioOperadores(conexion)

    def autenticar(self, usuario: str, clave: str) -> Operador | None:
        operador = self.operadores.buscar_por_usuario((usuario or "").strip())
        if operador and check_password_hash(operador.clave_hash, clave or ""):
            return operador
        return None
