# Autos Colombia · Sistema de parqueadero

Sistema de información para el parqueadero por mensualidad **Autos Colombia**.
Proyecto académico de Ingeniería de Software (IU Digital), desarrollado de forma iterativa.

**Iteración 1 — Gestión de la entrada y salida de vehículos.** Esta versión cubre esa gestión.
La gestión de usuarios y celdas (Iteración 2) y la de pagos (Iteración 3) se construirán sobre esta base.
Por ahora, los usuarios, vehículos y celdas se precargan como datos de demostración.

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

## Arquitectura

Es una arquitectura en capas, con una dependencia en un solo sentido:

```
parqueadero/
├── presentacion/   rutas Flask, plantillas HTML y CSS (captura, rechazo y confirmación)
├── aplicacion/     casos de uso: ServicioParqueo, ServicioAutenticacion
├── dominio/        entidades y reglas de negocio (RN-01 a RN-06) y sus excepciones
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

Abre http://127.0.0.1:5000 e ingresa con el usuario `operador` y la contraseña `autos2026`.

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

## Documentación

- `docs/diagramas/`: casos de uso, clases, paquetes, arquitectura, MER y modelo relacional (fuentes PlantUML y PNG)
- `docs/mockups/`: pantallas en sus tres estados (captura, rechazo y éxito)
- `parqueadero/persistencia/schema.sql`: modelo físico
