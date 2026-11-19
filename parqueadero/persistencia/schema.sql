-- Modelo físico - Autos Colombia, Iteraciones 1 (entrada y salida de vehículos),
-- 2 (gestión de usuarios, vehículos y celdas) y 3 (gestión de pagos)
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
    clave_hash   VARCHAR(255) NOT NULL,
    rol          VARCHAR(13)  NOT NULL DEFAULT 'OPERADOR'
                 CHECK (rol IN ('OPERADOR', 'ADMINISTRADOR'))
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

-- Iteración 2: búsquedas de usuarios por nombre y de vehículos por titular.
CREATE INDEX IF NOT EXISTS ix_usuario_nombre ON usuario (nombre);
CREATE INDEX IF NOT EXISTS ix_vehiculo_usuario ON vehiculo (id_usuario);

-- Iteración 3: tarifas y pagos de mensualidad. Los valores son enteros en pesos (RNF-17).
CREATE TABLE IF NOT EXISTS tarifa (
    tipo           VARCHAR(5) PRIMARY KEY CHECK (tipo IN ('CARRO', 'MOTO')),
    valor_mensual  INTEGER    NOT NULL CHECK (valor_mensual BETWEEN 10000 AND 2000000)
);

CREATE TABLE IF NOT EXISTS pago (
    id_pago                INTEGER PRIMARY KEY AUTOINCREMENT,
    id_vehiculo            INTEGER     NOT NULL REFERENCES vehiculo (id_vehiculo) ON DELETE RESTRICT,
    periodo                CHAR(7)     NOT NULL CHECK (periodo GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
    valor                  INTEGER     NOT NULL CHECK (valor > 0),
    medio                  VARCHAR(13) NOT NULL CHECK (medio IN ('EFECTIVO', 'TRANSFERENCIA', 'TARJETA')),
    referencia             VARCHAR(30),
    fecha_pago             TEXT        NOT NULL,
    id_operador            INTEGER     NOT NULL REFERENCES operador (id_operador),
    estado                 VARCHAR(7)  NOT NULL DEFAULT 'VIGENTE' CHECK (estado IN ('VIGENTE', 'ANULADO')),
    motivo_anulacion       VARCHAR(200),
    fecha_anulacion        TEXT,
    id_operador_anulacion  INTEGER     REFERENCES operador (id_operador),
    CHECK (medio = 'EFECTIVO' OR referencia IS NOT NULL),
    CHECK ((estado = 'ANULADO') = (motivo_anulacion IS NOT NULL))
);

-- RN-16 garantizada también por el motor: un solo pago vigente por vehículo y periodo.
CREATE UNIQUE INDEX IF NOT EXISTS ux_pago_vigente_periodo
    ON pago (id_vehiculo, periodo) WHERE estado = 'VIGENTE';
CREATE INDEX IF NOT EXISTS ix_pago_periodo ON pago (periodo);
