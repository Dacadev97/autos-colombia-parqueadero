import sqlite3
from pathlib import Path

ESQUEMA = Path(__file__).with_name("schema.sql")


def abrir_conexion(ruta: str) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta, check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _migrar(conexion: sqlite3.Connection) -> None:
    """Actualiza bases creadas en la Iteración 1: la tabla operador no tenía la columna rol."""
    columnas = {fila["name"] for fila in conexion.execute("PRAGMA table_info(operador)")}
    if "rol" not in columnas:
        with conexion:
            conexion.execute(
                "ALTER TABLE operador ADD COLUMN rol VARCHAR(13) NOT NULL DEFAULT 'OPERADOR' "
                "CHECK (rol IN ('OPERADOR', 'ADMINISTRADOR'))"
            )


def crear_esquema(conexion: sqlite3.Connection) -> None:
    tablas = {fila["name"] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "operador" in tablas:
        _migrar(conexion)
    conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
