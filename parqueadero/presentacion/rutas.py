"""Capa de presentación: recibe las acciones del operador y muestra resultados o rechazos.
Las reglas de negocio se validan en la capa de aplicación, nunca aquí."""

from functools import wraps

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for

from parqueadero.aplicacion.servicio_autenticacion import ServicioAutenticacion
from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.dominio.excepciones import ReglaNegocioError
from parqueadero.persistencia.conexion import abrir_conexion

bp = Blueprint("parqueadero", __name__)


def _conexion():
    if "conexion" not in g:
        g.conexion = abrir_conexion(current_app.config["DATABASE"])
    return g.conexion


@bp.teardown_app_request
def _cerrar_conexion(_error):
    conexion = g.pop("conexion", None)
    if conexion is not None:
        conexion.close()


def _servicio() -> ServicioParqueo:
    return ServicioParqueo(_conexion())


def requiere_sesion(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "operador_id" not in session:
            return redirect(url_for("parqueadero.iniciar_sesion"))
        return vista(*args, **kwargs)

    return envoltura


@bp.route("/login", methods=["GET", "POST"])
def iniciar_sesion():
    error = None
    if request.method == "POST":
        operador = ServicioAutenticacion(_conexion()).autenticar(
            request.form.get("usuario"), request.form.get("clave")
        )
        if operador:
            session.clear()
            session["operador_id"] = operador.id
            session["operador_nombre"] = operador.nombre
            return redirect(url_for("parqueadero.panel"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error)


@bp.route("/logout")
def cerrar_sesion():
    session.clear()
    return redirect(url_for("parqueadero.iniciar_sesion"))


@bp.route("/")
@requiere_sesion
def panel():
    servicio = _servicio()
    return render_template("panel.html", dentro=servicio.vehiculos_dentro(), celdas=servicio.resumen_celdas())


@bp.route("/entrada", methods=["GET", "POST"])
@requiere_sesion
def registrar_entrada():
    formulario = {"placa": "", "celda": "", "observacion": ""}
    error = resultado = None
    if request.method == "POST":
        formulario = {k: request.form.get(k, "") for k in formulario}
        try:
            resultado = _servicio().registrar_entrada(
                formulario["placa"], session["operador_id"], formulario["celda"], formulario["observacion"]
            )
        except ReglaNegocioError as rechazo:
            error = rechazo
    return render_template("entrada.html", formulario=formulario, error=error, resultado=resultado)


@bp.route("/salida", methods=["GET", "POST"])
@requiere_sesion
def registrar_salida():
    formulario = {"placa": request.args.get("placa", ""), "observacion": ""}
    error = resultado = None
    if request.method == "POST":
        formulario = {k: request.form.get(k, "") for k in formulario}
        try:
            resultado = _servicio().registrar_salida(
                formulario["placa"], session["operador_id"], formulario["observacion"]
            )
        except ReglaNegocioError as rechazo:
            error = rechazo
    return render_template("salida.html", formulario=formulario, error=error, resultado=resultado)


@bp.route("/historial")
@requiere_sesion
def historial():
    filtros = {k: request.args.get(k, "") for k in ("placa", "desde", "hasta")}
    registros = _servicio().historial(**filtros)
    return render_template("historial.html", filtros=filtros, registros=registros)
