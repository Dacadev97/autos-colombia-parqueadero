"""Acceso a datos. Ninguna regla de negocio vive aquí: solo consultas y escrituras."""

import sqlite3
from datetime import datetime

from parqueadero.dominio.entidades import (
    Celda,
    EstadoCelda,
    EstadoUsuario,
    Operador,
    RegistroParqueo,
    TipoVehiculo,
    Usuario,
    Vehiculo,
)

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def _a_texto(fecha: datetime | None) -> str | None:
    return fecha.strftime(FORMATO_FECHA) if fecha else None


def _a_fecha(texto: str | None) -> datetime | None:
    return datetime.strptime(texto, FORMATO_FECHA) if texto else None


class RepositorioUsuarios:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def buscar_por_id(self, id_usuario: int) -> Usuario | None:
        fila = self.conexion.execute(
            "SELECT * FROM usuario WHERE id_usuario = ?", (id_usuario,)
        ).fetchone()
        if fila is None:
            return None
        return Usuario(
            fila["id_usuario"], fila["documento"], fila["nombre"],
            fila["telefono"], EstadoUsuario(fila["estado"]),
        )


class RepositorioVehiculos:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def buscar_por_placa(self, placa: str) -> Vehiculo | None:
        fila = self.conexion.execute(
            "SELECT * FROM vehiculo WHERE placa = ?", (placa,)
        ).fetchone()
        if fila is None:
            return None
        return Vehiculo(
            fila["id_vehiculo"], fila["placa"], TipoVehiculo(fila["tipo"]),
            fila["marca"], fila["color"], fila["id_usuario"],
        )


class RepositorioCeldas:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    @staticmethod
    def _a_celda(fila) -> Celda:
        return Celda(fila["id_celda"], fila["codigo"], TipoVehiculo(fila["tipo"]), EstadoCelda(fila["estado"]))

    def buscar_por_codigo(self, codigo: str) -> Celda | None:
        fila = self.conexion.execute("SELECT * FROM celda WHERE codigo = ?", (codigo,)).fetchone()
        return self._a_celda(fila) if fila else None

    def buscar_por_id(self, id_celda: int) -> Celda | None:
        fila = self.conexion.execute("SELECT * FROM celda WHERE id_celda = ?", (id_celda,)).fetchone()
        return self._a_celda(fila) if fila else None

    def primera_disponible(self, tipo: TipoVehiculo) -> Celda | None:
        fila = self.conexion.execute(
            "SELECT * FROM celda WHERE tipo = ? AND estado = 'DISPONIBLE' ORDER BY codigo LIMIT 1",
            (tipo.value,),
        ).fetchone()
        return self._a_celda(fila) if fila else None

    def listar(self) -> list[Celda]:
        filas = self.conexion.execute("SELECT * FROM celda ORDER BY tipo, codigo").fetchall()
        return [self._a_celda(f) for f in filas]

    def actualizar_estado(self, id_celda: int, estado: EstadoCelda) -> None:
        self.conexion.execute("UPDATE celda SET estado = ? WHERE id_celda = ?", (estado.value, id_celda))


class RepositorioOperadores:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def buscar_por_usuario(self, usuario: str) -> Operador | None:
        fila = self.conexion.execute("SELECT * FROM operador WHERE usuario = ?", (usuario,)).fetchone()
        if fila is None:
            return None
        return Operador(fila["id_operador"], fila["usuario"], fila["nombre"], fila["clave_hash"])


class RepositorioRegistros:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    @staticmethod
    def _a_registro(fila) -> RegistroParqueo:
        return RegistroParqueo(
            id=fila["id_registro"],
            vehiculo_id=fila["id_vehiculo"],
            celda_id=fila["id_celda"],
            operador_entrada_id=fila["id_operador_entrada"],
            fecha_entrada=_a_fecha(fila["fecha_entrada"]),
            observacion_entrada=fila["observacion_entrada"],
            operador_salida_id=fila["id_operador_salida"],
            fecha_salida=_a_fecha(fila["fecha_salida"]),
            observacion_salida=fila["observacion_salida"],
        )

    def activo_por_vehiculo(self, id_vehiculo: int) -> RegistroParqueo | None:
        fila = self.conexion.execute(
            "SELECT * FROM registro_parqueo WHERE id_vehiculo = ? AND fecha_salida IS NULL",
            (id_vehiculo,),
        ).fetchone()
        return self._a_registro(fila) if fila else None

    def insertar(self, registro: RegistroParqueo) -> int:
        cursor = self.conexion.execute(
            """INSERT INTO registro_parqueo
               (id_vehiculo, id_celda, id_operador_entrada, fecha_entrada, observacion_entrada)
               VALUES (?, ?, ?, ?, ?)""",
            (registro.vehiculo_id, registro.celda_id, registro.operador_entrada_id,
             _a_texto(registro.fecha_entrada), registro.observacion_entrada),
        )
        return cursor.lastrowid

    def actualizar_salida(self, registro: RegistroParqueo) -> None:
        self.conexion.execute(
            """UPDATE registro_parqueo
               SET id_operador_salida = ?, fecha_salida = ?, observacion_salida = ?
               WHERE id_registro = ? AND fecha_salida IS NULL""",
            (registro.operador_salida_id, _a_texto(registro.fecha_salida),
             registro.observacion_salida, registro.id),
        )

    def listar_detalle(self, solo_activos: bool, placa: str | None = None,
                       desde: str | None = None, hasta: str | None = None) -> list[dict]:
        sql = """SELECT r.id_registro, v.placa, v.tipo, v.marca, v.color, u.nombre AS usuario,
                        c.codigo AS celda, r.fecha_entrada, r.fecha_salida,
                        r.observacion_entrada, r.observacion_salida
                 FROM registro_parqueo r
                 JOIN vehiculo v ON v.id_vehiculo = r.id_vehiculo
                 JOIN usuario u ON u.id_usuario = v.id_usuario
                 JOIN celda c ON c.id_celda = r.id_celda
                 WHERE 1 = 1"""
        parametros: list = []
        if solo_activos:
            sql += " AND r.fecha_salida IS NULL"
        if placa:
            sql += " AND v.placa = ?"
            parametros.append(placa)
        if desde:
            sql += " AND date(r.fecha_entrada) >= date(?)"
            parametros.append(desde)
        if hasta:
            sql += " AND date(r.fecha_entrada) <= date(?)"
            parametros.append(hasta)
        sql += " ORDER BY r.fecha_entrada DESC"
        return [dict(f) for f in self.conexion.execute(sql, parametros).fetchall()]
