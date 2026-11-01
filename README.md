# Autos Colombia · Sistema de parqueadero

Sistema de información para el parqueadero por mensualidad **Autos Colombia**.
Proyecto académico de Ingeniería de Software (IU Digital), desarrollado de forma iterativa.

- **Iteración 1 — Gestión de la entrada y salida de vehículos.**
- **Iteración 2 — Gestión de usuarios y gestión de celdas** (rama `feat/iteracion-2`): registro, consulta,
  actualización e inactivación de usuarios mensuales; registro, actualización y eliminación de sus vehículos;
  catálogo de celdas (crear, poner fuera de servicio, habilitar, eliminar), mapa de disponibilidad y
  reubicación de vehículos.
- La gestión de pagos (Iteración 3) se construirá sobre esta base.

Autores: Davidson Arley Cadavid Álvarez · Juan Pedro Montoya Vélez

## Funcionalidades

| Requerimiento | Descripción |
|---|---|
| RF-01 | Registrar la entrada de un vehículo registrado, con fecha y hora, y el estado del vehículo |
| RF-02 | Asignar automáticamente una celda disponible compatible con el tipo de vehículo, o validar la elegida |
| RF-03 | Rechazar entradas inválidas e informar el motivo (RN-01 a RN-03) |
| RF-04 | Registrar la salida, con fecha y hora y novedades, y liberar la celda |
| RF-05 | Rechazar salidas sin entrada activa (RN-05) |
| RF-06 | Consultar los vehículos dentro del parqueadero y la disponibilidad de celdas |
| RF-07 | Consultar el historial de entradas y salidas por placa y rango de fechas |
| RF-08 | Autenticación del operador |
| RF-09 | Registrar usuarios mensuales (documento único, nombre y teléfono) — RN-07 |
| RF-10 | Consultar usuarios por documento, nombre o estado y actualizar sus datos |
| RF-11 | Inactivar y reactivar usuarios (baja lógica que conserva el historial) — RN-08 |
| RF-12 | Registrar, actualizar y eliminar vehículos de un usuario; el tipo se deduce de la placa — RN-09, RN-10 |
| RF-13 | Crear y eliminar celdas (solo administrador) — RN-11, RN-13 |
| RF-14 | Poner celdas fuera de servicio y habilitarlas (solo administrador) — RN-12 |
| RF-15 | Consultar el mapa de celdas con su estado y el vehículo que ocupa cada una |
| RF-16 | Reubicar un vehículo que está dentro en otra celda disponible — RN-14 |

## Arquitectura

Es una arquitectura en capas, con una dependencia en un solo sentido:

```
parqueadero/
├── presentacion/   rutas Flask, plantillas HTML y CSS (captura, rechazo y confirmación)
├── aplicacion/     casos de uso: ServicioParqueo, ServicioAutenticacion, ServicioUsuarios, ServicioCeldas
├── dominio/        entidades y reglas de negocio (RN-00 a RN-14) y sus excepciones
└── persistencia/   repositorios SQL, conexión y schema.sql (modelo físico)
```

Las reglas de negocio se validan en la capa de aplicación y de dominio. Además, las reglas críticas
están protegidas en la base de datos mediante índices únicos parciales: un solo registro activo por
vehículo y por celda. La entrada y la salida se guardan en una sola transacción, así que el registro
y el estado de la celda nunca quedan contradictorios.

## Cómo ejecutarlo

Requisitos: Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Abre http://127.0.0.1:5000 e ingresa con uno de los usuarios de demostración:

| Usuario | Contraseña | Rol |
|---|---|---|
| `operador` | `autos2026` | Operador: entradas, salidas, usuarios, vehículos y reubicación |
| `admin` | `admin2026` | Administrador: además gestiona el catálogo de celdas |

Las bases creadas con la Iteración 1 se migran solas al iniciar (se agrega la columna `rol`).

Para probarlo puedes usar estos datos de demostración:

| Placa | Tipo | Titular | Resultado esperado |
|---|---|---|---|
| ABC123 | Carro | Laura Gómez (activa) | Entra y sale normalmente |
| XYZ789 | Carro | Carlos Restrepo (activo) | Entra y sale normalmente |
| FGH45K | Moto | Carlos Restrepo (activo) | Recibe una celda de moto (M-xx) |
| JKL321 | Carro | Marta Ruiz (**inactiva**) | Entrada rechazada (RN-01) |
| QQQ111 | — | No registrado | Entrada rechazada (RN-01) |

## Pruebas

```bash
pytest -q
```

Las pruebas siguen los criterios de aceptación *Dado–Cuando–Entonces* de las historias de usuario.
Las de la Iteración 2 (`test_servicio_usuarios.py`, `test_servicio_celdas.py`) se nombran como los casos
del plan de pruebas (`CP-01` a `CP-22`) y verifican los datos guardados, no solo el mensaje.

## Documentación

- `docs/diagramas/`: fuentes PlantUML (`.puml`) y PNG.
  - Iteración 1: casos de uso, clases, paquetes, arquitectura, MER y modelo relacional.
  - Iteración 2: `casos_uso_iteracion2`, `secuencia_it1_*` y `secuencia_it2_*` (secuencias de ambas
    iteraciones) y `componentes` (diagrama de componentes de las iteraciones 1 y 2).
  - Para regenerarlos: `plantuml -tpng docs/diagramas/*.puml`.
- `docs/mockups/`: pantallas en sus estados de captura, rechazo y éxito (01–09 de la Iteración 1,
  10–19 de la Iteración 2). Los de la Iteración 2 se regeneran con `python docs/mockups/generar_mockups.py`,
  que recorre las historias con la aplicación real y captura cada pantalla con Firefox en modo headless.
- `parqueadero/persistencia/schema.sql`: modelo físico
