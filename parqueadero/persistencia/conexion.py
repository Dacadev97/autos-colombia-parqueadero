import sqlite3
from pathlib import Path

ESQUEMA = Path(__file__).with_name("schema.sql")


def abrir_conexion(ruta: str) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta, check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_esquema(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
