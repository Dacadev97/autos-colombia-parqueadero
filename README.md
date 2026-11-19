# Autos Colombia · Sistema de parqueadero

Sistema de información para el parqueadero por mensualidad **Autos Colombia**.
Proyecto académico de Ingeniería de Software (IU Digital), desarrollado de forma iterativa.

- **Iteración 1 — Gestión de la entrada y salida de vehículos** (tag `iteracion-1`).
- **Iteración 2 — Gestión de usuarios y gestión de celdas** (tag `iteracion-2`, PR #1): registro, consulta,
  actualización e inactivación de usuarios mensuales; registro, actualización y eliminación de sus vehículos;
  catálogo de celdas (crear, poner fuera de servicio, habilitar, eliminar), mapa de disponibilidad y
  reubicación de vehículos.
- **Iteración 3 — Gestión de pagos** (tag `iteracion-3`, rama `feat/iteracion-3`): pago de la mensualidad por
  vehículo con recibo consecutivo, consulta de pagos y recaudo, estado de cuenta, anulación con motivo, tarifas
  mensuales por tipo de vehículo y verificación de la mensualidad al día en la entrada (paz y salvo).

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
| RF-21 | Registrar el pago de la mensualidad de un vehículo con el valor de la tarifa vigente y emitir el recibo — RN-15 a RN-18 |
| RF-22 | Consultar pagos por placa, mes y estado, y el recaudo del mes |
| RF-23 | Consultar el estado de cuenta de cada vehículo (al día o pendiente y último mes pagado) |
| RF-24 | Anular un pago con motivo (solo administrador); el mes vuelve a quedar pendiente — RN-20 |
| RF-25 | Configurar la tarifa mensual por tipo de vehículo (solo administrador) — RN-15 |
| RF-26 | Rechazar la entrada de un vehículo sin la mensualidad del mes pagada — RN-19 |
| RF-27 | Consultar e imprimir el recibo de pago |

## Arquitectura

Es una arquitectura en capas, con una dependencia en un solo sentido:

```
parqueadero/
├── presentacion/   rutas Flask, plantillas HTML y CSS (captura, rechazo y confirmación)
├── aplicacion/     casos de uso: ServicioParqueo, ServicioAutenticacion, ServicioUsuarios, ServicioCeldas,
│                   ServicioPagos
├── dominio/        entidades y reglas de negocio (RN-00 a RN-20) y sus excepciones
└── persistencia/   repositorios SQL, conexión y schema.sql (modelo físico)
```

Las reglas de negocio se validan en la capa de aplicación y de dominio. Además, las reglas críticas
están protegidas en la base de datos mediante índices únicos parciales: un solo registro activo por
vehículo y por celda, y un solo pago vigente por vehículo y mes. La entrada, la salida y cada pago se
guardan en una sola transacción, así que los datos nunca quedan a medias.

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
| `admin` | `admin2026` | Administrador: además gestiona el catálogo de celdas, anula pagos y fija tarifas |

Las bases creadas con la Iteración 1 se migran solas al iniciar (se agrega la columna `rol`); las de la
Iteración 2 reciben las tablas `tarifa` y `pago` y las tarifas de referencia.

Para probarlo puedes usar estos datos de demostración:

| Placa | Tipo | Titular | Resultado esperado |
|---|---|---|---|
| ABC123 | Carro | Laura Gómez (activa, al día de sep. a dic. 2026) | Entra y sale normalmente |
| XYZ789 | Carro | Carlos Restrepo (activo) | Entra y sale normalmente |
| FGH45K | Moto | Carlos Restrepo (activo) | Recibe una celda de moto (M-xx) |
| JKL321 | Carro | Marta Ruiz (**inactiva**) | Entrada rechazada (RN-01); no puede pagar (RN-18) |
| Vehículo nuevo | — | Titular activo, sin pagos | Entrada rechazada hasta pagar el mes (RN-19) |
| QQQ111 | — | No registrado | Entrada rechazada (RN-01) |

## Pruebas

```bash
pytest -q
```

Las pruebas siguen los criterios de aceptación *Dado–Cuando–Entonces* de las historias de usuario.
Las de las Iteraciones 2 y 3 se nombran como los casos del plan de pruebas (`CP-01` a `CP-24` para la
Iteración 2 y `CP-25` a `CP-40` para la Iteración 3, en `test_servicio_pagos.py` y
`test_rutas_iteracion3.py`) y verifican los datos guardados, no solo el mensaje.

## Documentación

- `docs/diagramas/`: fuentes PlantUML (`.puml`) y PNG.
  - Iteración 1: casos de uso, clases, paquetes, arquitectura, MER y modelo relacional.
  - Iteración 2: `casos_uso_iteracion2`, `secuencia_it1_*` y `secuencia_it2_*`.
  - Iteración 3: `casos_uso_iteracion3`, `secuencia_it3_*`, `secuencia_tres_iteraciones` (ciclo completo de
    un cliente a través de las 3 iteraciones) y `componentes` (actualizado con las 3 iteraciones).
  - Para regenerarlos: `plantuml -tpng docs/diagramas/*.puml`.
- `docs/mockups/`: pantallas en sus estados de captura, rechazo y éxito (01–09 de la Iteración 1,
  10–19 de la Iteración 2 y 20–27 de la Iteración 3). Los de las Iteraciones 2 y 3 se regeneran con
  `python docs/mockups/generar_mockups.py` (o `MOCKUPS_DESDE=20 …` solo para los de la Iteración 3),
  que recorre las historias con la aplicación real y captura cada pantalla con Firefox en modo headless.
- `parqueadero/persistencia/schema.sql`: modelo físico

## Evidencia por iteración

Cada iteración queda identificada en el historial con un tag y su propia rama o PR, de modo que se
puede ver exactamente qué cambió en cada una (`git diff iteracion-2..iteracion-3`).

| Iteración | Tag | Rama / PR | Commits principales | Archivos nuevos o modificados |
|---|---|---|---|---|
| 1. Entrada y salida | `iteracion-1` | `main` | hasta `05b6364` | `servicio_parqueo.py`, `servicio_autenticacion.py`, `entidades.py` (RN-00 a RN-06), plantillas de entrada, salida, panel e historial |
| 2. Usuarios y celdas | `iteracion-2` | PR #1 (`feat/iteracion-2`) | `0bfd635` a `bf2c376` | `servicio_usuarios.py`, `servicio_celdas.py`, reglas RN-07 a RN-14, `usuarios.html`, `usuario_detalle.html`, `celdas.html`, `test_servicio_usuarios.py`, `test_servicio_celdas.py` |
| 3. Pagos | `iteracion-3` | PR #2 (`feat/iteracion-3`) | desde `b561dfe` (todos los commits del PR #2) | `servicio_pagos.py`, reglas RN-15 a RN-20, tablas `tarifa` y `pago`, `RepositorioPagos`, `RepositorioTarifas`, `pagos.html`, `recibo.html`, `tarifas.html`, `test_servicio_pagos.py`, `test_rutas_iteracion3.py`, diagramas `*_iteracion3`/`secuencia_it3_*` y mockups 20–27 |

En la Iteración 3, `ServicioParqueo.registrar_entrada` incorpora la verificación de la mensualidad (RN-19),
y dos pruebas de la Iteración 2 se ajustaron para registrar el pago antes del ingreso, como exige esa regla.
