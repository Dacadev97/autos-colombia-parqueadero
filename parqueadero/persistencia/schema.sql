-- Modelo físico - Autos Colombia, Iteración 1 (entrada y salida de vehículos)
-- SGBD: SQLite 3. Fechas en TEXT con formato ISO 8601 'YYYY-MM-DD HH:MM:SS'.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario   INTEGER PRIMARY KEY AUTOINCREMENT,
    documento    VARCHAR(15)  NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    telefono     VARCHAR(15)  NOT NULL,
    estado       VARCHAR(10)  NOT NULL DEFAULT 'ACTIVO'
                 CHECK (estado IN ('ACTIVO', 'INACTIVO'))
);

CREATE TABLE IF NOT EXISTS vehiculo (
    id_vehiculo  INTEGER PRIMARY KEY AUTOINCREMENT,
    placa        VARCHAR(6)   NOT NULL UNIQUE,
    tipo         VARCHAR(5)   NOT NULL CHECK (tipo IN ('CARRO', 'MOTO')),
    marca        VARCHAR(30)  NOT NULL,
    color        VARCHAR(20)  NOT NULL,
    id_usuario   INTEGER      NOT NULL REFERENCES usuario (id_usuario) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS celda (
    id_celda     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo       VARCHAR(5)   NOT NULL UNIQUE,
    tipo         VARCHAR(5)   NOT NULL CHECK (tipo IN ('CARRO', 'MOTO')),
    estado       VARCHAR(17)  NOT NULL DEFAULT 'DISPONIBLE'
                 CHECK (estado IN ('DISPONIBLE', 'OCUPADA', 'FUERA_DE_SERVICIO'))
);

CREATE TABLE IF NOT EXISTS operador (
    id_operador  INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario      VARCHAR(30)  NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    clave_hash   VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS registro_parqueo (
    id_registro          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_vehiculo          INTEGER  NOT NULL REFERENCES vehiculo (id_vehiculo) ON DELETE RESTRICT,
    id_celda             INTEGER  NOT NULL REFERENCES celda (id_celda) ON DELETE RESTRICT,
    id_operador_entrada  INTEGER  NOT NULL REFERENCES operador (id_operador),
    fecha_entrada        TEXT     NOT NULL,
    observacion_entrada  VARCHAR(255),
    id_operador_salida   INTEGER  REFERENCES operador (id_operador),
    fecha_salida         TEXT,
    observacion_salida   VARCHAR(255),
    CHECK (fecha_salida IS NULL OR fecha_salida >= fecha_entrada),
    CHECK ((fecha_salida IS NULL) = (id_operador_salida IS NULL))
);

-- RN-02 y RN-03 también garantizadas por el motor: como máximo un registro
-- activo (sin fecha de salida) por vehículo y por celda.
CREATE UNIQUE INDEX IF NOT EXISTS ux_registro_activo_vehiculo
    ON registro_parqueo (id_vehiculo) WHERE fecha_salida IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_registro_activo_celda
    ON registro_parqueo (id_celda) WHERE fecha_salida IS NULL;
CREATE INDEX IF NOT EXISTS ix_registro_fecha_entrada
    ON registro_parqueo (fecha_entrada);
