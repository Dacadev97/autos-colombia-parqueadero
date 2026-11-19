"""Datos de demostración. Desde la Iteración 2, usuarios, vehículos y celdas se gestionan
desde la aplicación, y desde la Iteración 3 también las tarifas y los pagos; estos datos solo
dejan el sistema listo para probarlo."""

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


# Iteración 3: tarifas mensuales por tipo de vehículo y mensualidades ya pagadas.
TARIFAS = [("CARRO", 180_000), ("MOTO", 70_000)]
PERIODOS_PAGADOS = ["2026-09", "2026-10", "2026-11", "2026-12"]
PLACAS_AL_DIA = {"ABC123": "EFECTIVO", "XYZ789": "TRANSFERENCIA", "FGH45K": "EFECTIVO"}


def _asegurar_tarifas(conexion: sqlite3.Connection) -> None:
    """Una base que viene de la Iteración 2 no tiene tarifas: se crean las de referencia."""
    with conexion:
        conexion.executemany("INSERT OR IGNORE INTO tarifa (tipo, valor_mensual) VALUES (?, ?)", TARIFAS)


def _cargar_pagos_demo(conexion: sqlite3.Connection) -> None:
    tarifas = dict(TARIFAS)
    filas = conexion.execute(
        "SELECT id_vehiculo, placa, tipo FROM vehiculo WHERE placa IN (%s) ORDER BY placa"
        % ",".join("?" * len(PLACAS_AL_DIA)), list(PLACAS_AL_DIA)
    ).fetchall()
    pagos = []
    for periodo in PERIODOS_PAGADOS:
        for fila in filas:
            medio = PLACAS_AL_DIA[fila["placa"]]
            referencia = f"TRF{periodo.replace('-', '')}{fila['id_vehiculo']:02d}" if medio != "EFECTIVO" else None
            pagos.append((fila["id_vehiculo"], periodo, tarifas[fila["tipo"]], medio, referencia,
                          f"{periodo}-01 08:00:00", 1))
    with conexion:
        conexion.executemany(
            "INSERT INTO pago (id_vehiculo, periodo, valor, medio, referencia, fecha_pago, id_operador) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", pagos
        )


def _asegurar_administrador(conexion: sqlite3.Connection) -> None:
    if conexion.execute("SELECT COUNT(*) FROM operador WHERE rol = 'ADMINISTRADOR'").fetchone()[0]:
        return
    with conexion:
        conexion.execute(
            "INSERT INTO operador (usuario, nombre, clave_hash, rol) VALUES (?, ?, ?, 'ADMINISTRADOR')",
            ("admin", "Administrador", generate_password_hash("admin2026")),
        )


def cargar_datos_demo(conexion: sqlite3.Connection) -> None:
    if conexion.execute("SELECT COUNT(*) FROM operador").fetchone()[0]:
        _asegurar_administrador(conexion)
        _asegurar_tarifas(conexion)
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
    _asegurar_tarifas(conexion)
    _cargar_pagos_demo(conexion)
