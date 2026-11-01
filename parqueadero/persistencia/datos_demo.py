"""Datos de demostración. Desde la Iteración 2, usuarios, vehículos y celdas se gestionan
desde la aplicación; estos datos solo dejan el sistema listo para probarlo."""

import sqlite3

from werkzeug.security import generate_password_hash

USUARIOS = [
    ("1036000001", "Laura Gómez", "3001234567", "ACTIVO"),
    ("1036000002", "Carlos Restrepo", "3017654321", "ACTIVO"),
    ("1036000003", "Marta Ruiz", "3024567890", "INACTIVO"),
]
VEHICULOS = [
    ("ABC123", "CARRO", "Renault", "Gris", 1),
    ("XYZ789", "CARRO", "Mazda", "Rojo", 2),
    ("FGH45K", "MOTO", "Yamaha", "Negro", 2),
    ("JKL321", "CARRO", "Chevrolet", "Blanco", 3),
]


def _asegurar_administrador(conexion: sqlite3.Connection) -> None:
    if conexion.execute("SELECT COUNT(*) FROM operador WHERE rol = 'ADMINISTRADOR'").fetchone()[0]:
        return
    with conexion:
        conexion.execute(
            "INSERT INTO operador (usuario, nombre, clave_hash, rol) VALUES (?, ?, ?, 'ADMINISTRADOR')",
            ("admin", "Administrador del parqueadero", generate_password_hash("admin2026")),
        )


def cargar_datos_demo(conexion: sqlite3.Connection) -> None:
    if conexion.execute("SELECT COUNT(*) FROM operador").fetchone()[0]:
        _asegurar_administrador(conexion)
        return
    with conexion:
        conexion.execute(
            "INSERT INTO operador (usuario, nombre, clave_hash) VALUES (?, ?, ?)",
            ("operador", "Operador de turno", generate_password_hash("autos2026")),
        )
        conexion.executemany(
            "INSERT INTO usuario (documento, nombre, telefono, estado) VALUES (?, ?, ?, ?)", USUARIOS
        )
        conexion.executemany(
            "INSERT INTO vehiculo (placa, tipo, marca, color, id_usuario) VALUES (?, ?, ?, ?, ?)", VEHICULOS
        )
        celdas = [(f"C-{n:02d}", "CARRO", "DISPONIBLE") for n in range(1, 11)]
        celdas += [(f"M-{n:02d}", "MOTO", "DISPONIBLE") for n in range(1, 6)]
        celdas[9] = ("C-10", "CARRO", "FUERA_DE_SERVICIO")
        conexion.executemany("INSERT INTO celda (codigo, tipo, estado) VALUES (?, ?, ?)", celdas)
    _asegurar_administrador(conexion)
