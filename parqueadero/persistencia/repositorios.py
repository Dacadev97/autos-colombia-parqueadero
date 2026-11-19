"""Acceso a datos. Ninguna regla de negocio vive aquí: solo consultas y escrituras."""

import sqlite3
from datetime import datetime

from parqueadero.dominio.entidades import (
    Celda,
    EstadoCelda,
    EstadoPago,
    EstadoUsuario,
    MedioPago,
    Operador,
    Pago,
    RegistroParqueo,
    RolOperador,
    Tarifa,
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

    @staticmethod
    def _a_usuario(fila) -> Usuario:
        return Usuario(
            fila["id_usuario"], fila["documento"], fila["nombre"],
            fila["telefono"], EstadoUsuario(fila["estado"]),
        )

    def buscar_por_id(self, id_usuario: int) -> Usuario | None:
        fila = self.conexion.execute(
            "SELECT * FROM usuario WHERE id_usuario = ?", (id_usuario,)
        ).fetchone()
        return self._a_usuario(fila) if fila else None

    def buscar_por_documento(self, documento: str) -> Usuario | None:
        fila = self.conexion.execute("SELECT * FROM usuario WHERE documento = ?", (documento,)).fetchone()
        return self._a_usuario(fila) if fila else None

    def listar(self, texto: str | None = None, estado: EstadoUsuario | None = None) -> list[dict]:
        sql = """SELECT u.id_usuario, u.documento, u.nombre, u.telefono, u.estado,
                        COUNT(v.id_vehiculo) AS vehiculos
                 FROM usuario u LEFT JOIN vehiculo v ON v.id_usuario = u.id_usuario
                 WHERE 1 = 1"""
        parametros: list = []
        if texto:
            sql += " AND (u.documento LIKE ? OR u.nombre LIKE ?)"
            parametros += [f"%{texto}%", f"%{texto}%"]
        if estado:
            sql += " AND u.estado = ?"
            parametros.append(estado.value)
        sql += " GROUP BY u.id_usuario ORDER BY u.nombre"
        return [dict(f) for f in self.conexion.execute(sql, parametros).fetchall()]

    def insertar(self, usuario: Usuario) -> int:
        cursor = self.conexion.execute(
            "INSERT INTO usuario (documento, nombre, telefono, estado) VALUES (?, ?, ?, ?)",
            (usuario.documento, usuario.nombre, usuario.telefono, usuario.estado.value),
        )
        return cursor.lastrowid

    def actualizar(self, usuario: Usuario) -> None:
        self.conexion.execute(
            "UPDATE usuario SET nombre = ?, telefono = ?, estado = ? WHERE id_usuario = ?",
            (usuario.nombre, usuario.telefono, usuario.estado.value, usuario.id),
        )


class RepositorioVehiculos:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    @staticmethod
    def _a_vehiculo(fila) -> Vehiculo:
        return Vehiculo(
            fila["id_vehiculo"], fila["placa"], TipoVehiculo(fila["tipo"]),
            fila["marca"], fila["color"], fila["id_usuario"],
        )

    def buscar_por_placa(self, placa: str) -> Vehiculo | None:
        fila = self.conexion.execute(
            "SELECT * FROM vehiculo WHERE placa = ?", (placa,)
        ).fetchone()
        return self._a_vehiculo(fila) if fila else None

    def buscar_por_id(self, id_vehiculo: int) -> Vehiculo | None:
        fila = self.conexion.execute("SELECT * FROM vehiculo WHERE id_vehiculo = ?", (id_vehiculo,)).fetchone()
        return self._a_vehiculo(fila) if fila else None

    def listar_por_usuario(self, id_usuario: int) -> list[dict]:
        filas = self.conexion.execute(
            """SELECT v.id_vehiculo, v.placa, v.tipo, v.marca, v.color, c.codigo AS celda
               FROM vehiculo v
               LEFT JOIN registro_parqueo r ON r.id_vehiculo = v.id_vehiculo AND r.fecha_salida IS NULL
               LEFT JOIN celda c ON c.id_celda = r.id_celda
               WHERE v.id_usuario = ? ORDER BY v.placa""",
            (id_usuario,),
        ).fetchall()
        return [dict(f) for f in filas]

    def insertar(self, vehiculo: Vehiculo) -> int:
        cursor = self.conexion.execute(
            "INSERT INTO vehiculo (placa, tipo, marca, color, id_usuario) VALUES (?, ?, ?, ?, ?)",
            (vehiculo.placa, vehiculo.tipo.value, vehiculo.marca, vehiculo.color, vehiculo.usuario_id),
        )
        return cursor.lastrowid

    def actualizar(self, vehiculo: Vehiculo) -> None:
        self.conexion.execute(
            "UPDATE vehiculo SET marca = ?, color = ? WHERE id_vehiculo = ?",
            (vehiculo.marca, vehiculo.color, vehiculo.id),
        )

    def eliminar(self, id_vehiculo: int) -> None:
        self.conexion.execute("DELETE FROM vehiculo WHERE id_vehiculo = ?", (id_vehiculo,))


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

    def listar_con_ocupacion(self, tipo: TipoVehiculo | None = None,
                             estado: EstadoCelda | None = None) -> list[dict]:
        sql = """SELECT c.id_celda, c.codigo, c.tipo, c.estado, v.placa, u.nombre AS usuario
                 FROM celda c
                 LEFT JOIN registro_parqueo r ON r.id_celda = c.id_celda AND r.fecha_salida IS NULL
                 LEFT JOIN vehiculo v ON v.id_vehiculo = r.id_vehiculo
                 LEFT JOIN usuario u ON u.id_usuario = v.id_usuario
                 WHERE 1 = 1"""
        parametros: list = []
        if tipo:
            sql += " AND c.tipo = ?"
            parametros.append(tipo.value)
        if estado:
            sql += " AND c.estado = ?"
            parametros.append(estado.value)
        sql += " ORDER BY c.tipo, c.codigo"
        return [dict(f) for f in self.conexion.execute(sql, parametros).fetchall()]

    def insertar(self, celda: Celda) -> int:
        cursor = self.conexion.execute(
            "INSERT INTO celda (codigo, tipo, estado) VALUES (?, ?, ?)",
            (celda.codigo, celda.tipo.value, celda.estado.value),
        )
        return cursor.lastrowid

    def eliminar(self, id_celda: int) -> None:
        self.conexion.execute("DELETE FROM celda WHERE id_celda = ?", (id_celda,))


class RepositorioOperadores:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def buscar_por_usuario(self, usuario: str) -> Operador | None:
        fila = self.conexion.execute("SELECT * FROM operador WHERE usuario = ?", (usuario,)).fetchone()
        if fila is None:
            return None
        return Operador(
            fila["id_operador"], fila["usuario"], fila["nombre"], fila["clave_hash"], RolOperador(fila["rol"])
        )


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

    def contar_por_vehiculo(self, id_vehiculo: int) -> int:
        return self.conexion.execute(
            "SELECT COUNT(*) FROM registro_parqueo WHERE id_vehiculo = ?", (id_vehiculo,)
        ).fetchone()[0]

    def contar_por_celda(self, id_celda: int) -> int:
        return self.conexion.execute(
            "SELECT COUNT(*) FROM registro_parqueo WHERE id_celda = ?", (id_celda,)
        ).fetchone()[0]

    def actualizar_celda(self, id_registro: int, id_celda: int) -> None:
        self.conexion.execute(
            "UPDATE registro_parqueo SET id_celda = ? WHERE id_registro = ? AND fecha_salida IS NULL",
            (id_celda, id_registro),
        )

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


# --- Iteración 3: tarifas y pagos ------------------------------------------------------------------

class RepositorioTarifas:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    def obtener(self, tipo: TipoVehiculo) -> Tarifa | None:
        fila = self.conexion.execute("SELECT * FROM tarifa WHERE tipo = ?", (tipo.value,)).fetchone()
        return Tarifa(TipoVehiculo(fila["tipo"]), fila["valor_mensual"]) if fila else None

    def listar(self) -> list[Tarifa]:
        filas = self.conexion.execute("SELECT * FROM tarifa ORDER BY tipo").fetchall()
        return [Tarifa(TipoVehiculo(f["tipo"]), f["valor_mensual"]) for f in filas]

    def guardar(self, tarifa: Tarifa) -> None:
        self.conexion.execute(
            "INSERT INTO tarifa (tipo, valor_mensual) VALUES (?, ?) "
            "ON CONFLICT (tipo) DO UPDATE SET valor_mensual = excluded.valor_mensual",
            (tarifa.tipo.value, tarifa.valor_mensual),
        )


class RepositorioPagos:
    def __init__(self, conexion: sqlite3.Connection):
        self.conexion = conexion

    @staticmethod
    def _a_pago(fila) -> Pago:
        return Pago(
            id=fila["id_pago"], vehiculo_id=fila["id_vehiculo"], periodo=fila["periodo"], valor=fila["valor"],
            medio=MedioPago(fila["medio"]), referencia=fila["referencia"], fecha_pago=_a_fecha(fila["fecha_pago"]),
            operador_id=fila["id_operador"], estado=EstadoPago(fila["estado"]),
            motivo_anulacion=fila["motivo_anulacion"], fecha_anulacion=_a_fecha(fila["fecha_anulacion"]),
            operador_anulacion_id=fila["id_operador_anulacion"],
        )

    def buscar_por_id(self, id_pago: int) -> Pago | None:
        fila = self.conexion.execute("SELECT * FROM pago WHERE id_pago = ?", (id_pago,)).fetchone()
        return self._a_pago(fila) if fila else None

    def vigente(self, id_vehiculo: int, periodo: str) -> Pago | None:
        fila = self.conexion.execute(
            "SELECT * FROM pago WHERE id_vehiculo = ? AND periodo = ? AND estado = 'VIGENTE'", (id_vehiculo, periodo)
        ).fetchone()
        return self._a_pago(fila) if fila else None

    def periodos_pagados(self, id_vehiculo: int) -> list[str]:
        filas = self.conexion.execute(
            "SELECT periodo FROM pago WHERE id_vehiculo = ? AND estado = 'VIGENTE' ORDER BY periodo",
            (id_vehiculo,),
        ).fetchall()
        return [f["periodo"] for f in filas]

    def insertar(self, pago: Pago) -> int:
        cursor = self.conexion.execute(
            """INSERT INTO pago (id_vehiculo, periodo, valor, medio, referencia, fecha_pago, id_operador, estado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pago.vehiculo_id, pago.periodo, pago.valor, pago.medio.value, pago.referencia,
             _a_texto(pago.fecha_pago), pago.operador_id, pago.estado.value),
        )
        return cursor.lastrowid

    def actualizar_anulacion(self, pago: Pago) -> None:
        self.conexion.execute(
            """UPDATE pago SET estado = ?, motivo_anulacion = ?, fecha_anulacion = ?, id_operador_anulacion = ?
               WHERE id_pago = ? AND estado = 'VIGENTE'""",
            (pago.estado.value, pago.motivo_anulacion, _a_texto(pago.fecha_anulacion),
             pago.operador_anulacion_id, pago.id),
        )

    def listar_detalle(self, placa: str | None = None, periodo: str | None = None,
                       estado: EstadoPago | None = None) -> list[dict]:
        sql = """SELECT p.id_pago, printf('REC-%06d', p.id_pago) AS recibo, p.periodo, p.valor, p.medio,
                        p.referencia, p.fecha_pago, p.estado, p.motivo_anulacion, v.placa, v.tipo,
                        u.nombre AS usuario, o.nombre AS operador
                 FROM pago p
                 JOIN vehiculo v ON v.id_vehiculo = p.id_vehiculo
                 JOIN usuario u ON u.id_usuario = v.id_usuario
                 JOIN operador o ON o.id_operador = p.id_operador
                 WHERE 1 = 1"""
        parametros: list = []
        if placa:
            sql += " AND v.placa = ?"
            parametros.append(placa)
        if periodo:
            sql += " AND p.periodo = ?"
            parametros.append(periodo)
        if estado:
            sql += " AND p.estado = ?"
            parametros.append(estado.value)
        sql += " ORDER BY p.fecha_pago DESC, p.id_pago DESC"
        return [dict(f) for f in self.conexion.execute(sql, parametros).fetchall()]

    def recaudo(self, periodo: str | None = None) -> int:
        """Suma de pagos vigentes (los anulados no cuentan como recaudo)."""
        sql, parametros = "SELECT COALESCE(SUM(valor), 0) FROM pago WHERE estado = 'VIGENTE'", []
        if periodo:
            sql += " AND periodo = ?"
            parametros.append(periodo)
        return self.conexion.execute(sql, parametros).fetchone()[0]
