"""Capa de presentación: recibe las acciones del operador y muestra resultados o rechazos.
Las reglas de negocio se validan en la capa de aplicación, nunca aquí."""

from functools import wraps

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for,
)

from parqueadero.aplicacion.servicio_autenticacion import ServicioAutenticacion
from parqueadero.aplicacion.servicio_celdas import ServicioCeldas
from parqueadero.aplicacion.servicio_parqueo import ServicioParqueo
from parqueadero.aplicacion.servicio_usuarios import ServicioUsuarios
from parqueadero.dominio.entidades import EstadoCelda, EstadoUsuario, RolOperador
from parqueadero.dominio.excepciones import (
    CeldaNoEncontrada, ReglaNegocioError, UsuarioNoEncontrado, VehiculoNoEncontrado,
)
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


def requiere_administrador(vista):
    """RNF-09: las operaciones sobre el catálogo de celdas son exclusivas del administrador."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "operador_id" not in session:
            return redirect(url_for("parqueadero.iniciar_sesion"))
        if session.get("operador_rol") != RolOperador.ADMINISTRADOR.value:
            abort(403)
        return vista(*args, **kwargs)

    return envoltura


@bp.app_errorhandler(403)
def _acceso_denegado(_error):
    return render_template("acceso_denegado.html"), 403


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
            session["operador_rol"] = operador.rol.value
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


# --- Iteración 2: gestión de usuarios y vehículos ------------------------------------------------

def _usuario_o_404(servicio: ServicioUsuarios, id_usuario: int):
    try:
        return servicio.obtener_usuario(id_usuario)
    except UsuarioNoEncontrado:
        abort(404)


@bp.route("/usuarios", methods=["GET", "POST"])
@requiere_sesion
def usuarios():
    servicio = ServicioUsuarios(_conexion())
    filtros = {k: request.args.get(k, "") for k in ("texto", "estado")}
    formulario = {"documento": "", "nombre": "", "telefono": ""}
    error = None
    if request.method == "POST":
        formulario = {k: request.form.get(k, "") for k in formulario}
        try:
            usuario = servicio.registrar_usuario(**formulario)
            flash(f"Usuario {usuario.nombre} registrado. Ahora registre sus vehículos.", "exito")
            return redirect(url_for("parqueadero.detalle_usuario", id_usuario=usuario.id))
        except ReglaNegocioError as rechazo:
            error = rechazo
    return render_template(
        "usuarios.html", usuarios=servicio.listar_usuarios(**filtros), filtros=filtros,
        formulario=formulario, error=error,
    )


def _render_detalle(servicio, usuario, error=None, formulario_vehiculo=None):
    return render_template(
        "usuario_detalle.html", usuario=usuario, vehiculos=servicio.vehiculos_de(usuario.id), error=error,
        formulario_vehiculo=formulario_vehiculo or {"placa": "", "marca": "", "color": ""},
    )


@bp.route("/usuarios/<int:id_usuario>", methods=["GET", "POST"])
@requiere_sesion
def detalle_usuario(id_usuario):
    servicio = ServicioUsuarios(_conexion())
    usuario = _usuario_o_404(servicio, id_usuario)
    if request.method == "POST":
        try:
            servicio.actualizar_usuario(id_usuario, request.form.get("nombre"), request.form.get("telefono"))
            flash("Datos del usuario actualizados.", "exito")
            return redirect(url_for("parqueadero.detalle_usuario", id_usuario=id_usuario))
        except ReglaNegocioError as rechazo:
            usuario.nombre, usuario.telefono = request.form.get("nombre", ""), request.form.get("telefono", "")
            return _render_detalle(servicio, usuario, error=rechazo)
    return _render_detalle(servicio, usuario)


@bp.route("/usuarios/<int:id_usuario>/estado", methods=["POST"])
@requiere_sesion
def cambiar_estado_usuario(id_usuario):
    servicio = ServicioUsuarios(_conexion())
    _usuario_o_404(servicio, id_usuario)
    try:
        usuario = servicio.cambiar_estado(id_usuario, EstadoUsuario(request.form.get("estado")))
        flash(f"El usuario quedó {usuario.estado.value.lower()}.", "exito")
    except (ReglaNegocioError, ValueError) as rechazo:
        flash(getattr(rechazo, "mensaje", "Estado no válido."), "error")
    return redirect(url_for("parqueadero.detalle_usuario", id_usuario=id_usuario))


@bp.route("/usuarios/<int:id_usuario>/vehiculos", methods=["POST"])
@requiere_sesion
def registrar_vehiculo(id_usuario):
    servicio = ServicioUsuarios(_conexion())
    usuario = _usuario_o_404(servicio, id_usuario)
    formulario = {k: request.form.get(k, "") for k in ("placa", "marca", "color")}
    try:
        vehiculo = servicio.registrar_vehiculo(id_usuario, **formulario)
        flash(f"Vehículo {vehiculo.placa} ({vehiculo.tipo.value.lower()}) registrado.", "exito")
        return redirect(url_for("parqueadero.detalle_usuario", id_usuario=id_usuario))
    except ReglaNegocioError as rechazo:
        return _render_detalle(servicio, usuario, error=rechazo, formulario_vehiculo=formulario)


@bp.route("/vehiculos/<int:id_vehiculo>", methods=["POST"])
@requiere_sesion
def actualizar_vehiculo(id_vehiculo):
    servicio = ServicioUsuarios(_conexion())
    try:
        vehiculo = servicio.obtener_vehiculo(id_vehiculo)
    except VehiculoNoEncontrado:
        abort(404)
    try:
        if request.form.get("accion") == "eliminar":
            servicio.eliminar_vehiculo(id_vehiculo)
            flash(f"Vehículo {vehiculo.placa} eliminado.", "exito")
        else:
            servicio.actualizar_vehiculo(id_vehiculo, request.form.get("marca"), request.form.get("color"))
            flash(f"Vehículo {vehiculo.placa} actualizado.", "exito")
    except ReglaNegocioError as rechazo:
        flash(f"Operación rechazada ({rechazo.codigo}). {rechazo.mensaje}", "error")
    return redirect(url_for("parqueadero.detalle_usuario", id_usuario=vehiculo.usuario_id))


# --- Iteración 2: gestión de celdas --------------------------------------------------------------

def _render_celdas(servicio, error=None, formulario=None, status=200):
    filtros = {k: request.args.get(k, "") for k in ("tipo", "estado")}
    return render_template(
        "celdas.html", celdas=servicio.listar(**filtros), filtros=filtros, error=error,
        formulario=formulario or {"codigo": "", "placa": "", "destino": ""},
        resumen=ServicioParqueo(_conexion()).resumen_celdas(),
    ), status


@bp.route("/celdas")
@requiere_sesion
def celdas():
    return _render_celdas(ServicioCeldas(_conexion()))


@bp.route("/celdas", methods=["POST"])
@requiere_administrador
def crear_celda():
    servicio = ServicioCeldas(_conexion())
    codigo = request.form.get("codigo", "")
    try:
        celda = servicio.crear_celda(codigo)
        flash(f"Celda {celda.codigo} creada y disponible.", "exito")
        return redirect(url_for("parqueadero.celdas"))
    except ReglaNegocioError as rechazo:
        return _render_celdas(servicio, error=rechazo, formulario={"codigo": codigo, "placa": "", "destino": ""})


@bp.route("/celdas/<int:id_celda>/estado", methods=["POST"])
@requiere_administrador
def cambiar_estado_celda(id_celda):
    servicio = ServicioCeldas(_conexion())
    try:
        if request.form.get("accion") == "eliminar":
            celda = servicio.eliminar_celda(id_celda)
            flash(f"Celda {celda.codigo} eliminada.", "exito")
        else:
            celda = servicio.cambiar_estado(id_celda, EstadoCelda(request.form.get("estado")))
            flash(f"La celda {celda.codigo} quedó {celda.estado.value.replace('_', ' ').lower()}.", "exito")
    except CeldaNoEncontrada:
        abort(404)
    except (ReglaNegocioError, ValueError) as rechazo:
        mensaje = f"Operación rechazada ({rechazo.codigo}). {rechazo.mensaje}" \
            if isinstance(rechazo, ReglaNegocioError) else "Estado no válido."
        flash(mensaje, "error")
    return redirect(url_for("parqueadero.celdas"))


@bp.route("/celdas/reubicar", methods=["POST"])
@requiere_sesion
def reubicar_vehiculo():
    servicio = ServicioCeldas(_conexion())
    formulario = {"codigo": "", "placa": request.form.get("placa", ""), "destino": request.form.get("destino", "")}
    try:
        resultado = servicio.reubicar_vehiculo(formulario["placa"], formulario["destino"])
        flash(f"Vehículo {resultado.vehiculo.placa} reubicado en la celda {resultado.celda.codigo}.", "exito")
        return redirect(url_for("parqueadero.celdas"))
    except ReglaNegocioError as rechazo:
        return _render_celdas(servicio, error=rechazo, formulario=formulario)
