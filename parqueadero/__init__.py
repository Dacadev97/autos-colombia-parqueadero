import os
from pathlib import Path

from flask import Flask

from parqueadero.persistencia.conexion import abrir_conexion, crear_esquema
from parqueadero.persistencia.datos_demo import cargar_datos_demo


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="presentacion/templates", static_folder="presentacion/static")
    app.config.update(
        SECRET_KEY=os.environ.get("PARQUEADERO_SECRET_KEY", "dev-autos-colombia"),
        DATABASE=os.environ.get("PARQUEADERO_DB", str(Path(app.instance_path) / "parqueadero.db")),
        CARGAR_DEMO=True,
    )
    if config:
        app.config.update(config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    conexion = abrir_conexion(app.config["DATABASE"])
    crear_esquema(conexion)
    if app.config["CARGAR_DEMO"]:
        cargar_datos_demo(conexion)
    conexion.close()

    from parqueadero.presentacion.rutas import bp

    app.register_blueprint(bp)
    return app
