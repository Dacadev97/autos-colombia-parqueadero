"""Genera los mockups de las Iteraciones 2 y 3 a partir de las pantallas reales de la aplicación.

Uso:  python docs/mockups/generar_mockups.py [ruta-de-firefox]
      MOCKUPS_DESDE=20 python docs/mockups/generar_mockups.py   (solo los mockups 20 en adelante)

1. Crea una base temporal con los datos de demostración y recorre cada historia de usuario con el
   cliente de pruebas de Flask (estados de captura, rechazo y confirmación).
2. Guarda cada pantalla como HTML autocontenido (CSS en línea) en docs/mockups/html/.
3. Captura cada HTML como PNG con Firefox en modo headless (perfil temporal, sin tocar el del usuario).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from parqueadero import create_app  # noqa: E402

SALIDA = Path(__file__).resolve().parent
CSS = (RAIZ / "parqueadero/presentacion/static/estilos.css").read_text(encoding="utf-8")
ANCHO = 1100


def _autocontenido(html: str) -> str:
    inicio = html.index('<link rel="stylesheet"')
    fin = html.index(">", inicio) + 1
    return html[:inicio] + f"<style>{CSS}</style>" + html[fin:]


def _cliente(app, usuario, clave):
    cliente = app.test_client()
    cliente.post("/login", data={"usuario": usuario, "clave": clave})
    return cliente


def pantallas(app) -> list[tuple[str, int, str]]:
    """Devuelve (nombre, alto en px, html) de cada mockup, en el orden de las historias."""
    operador = _cliente(app, "operador", "autos2026")
    admin = _cliente(app, "admin", "admin2026")
    texto = lambda r: r.get_data(as_text=True)  # noqa: E731
    capturas = []

    # HU-07 / HU-08: lista de usuarios con formulario de registro (captura).
    capturas.append(("10_usuarios_lista", 640, texto(operador.get("/usuarios"))))
    # HU-07: rechazo por documento duplicado (RN-07), conserva lo digitado.
    capturas.append(("11_usuario_rechazo", 640, texto(operador.post("/usuarios", data={
        "documento": "1036000001", "nombre": "Andrés Felipe Toro", "telefono": "3155550101"}))))
    # HU-07: confirmación, el sistema lleva a la ficha del nuevo usuario.
    capturas.append(("12_usuario_registrado", 720, texto(operador.post("/usuarios", data={
        "documento": "1036000004", "nombre": "Andrés Felipe Toro", "telefono": "3155550101"},
        follow_redirects=True))))
    # HU-10: vehículo registrado, tipo deducido de la placa.
    operador.post("/usuarios/4/vehiculos", data={"placa": "DEF456", "marca": "Kia", "color": "Azul"},
                  follow_redirects=True)
    capturas.append(("13_vehiculo_registrado", 760, texto(operador.post("/usuarios/4/vehiculos", data={
        "placa": "MNO12P", "marca": "Honda", "color": "Rojo"}, follow_redirects=True))))
    # HU-10: rechazo por placa duplicada (RN-09).
    capturas.append(("14_vehiculo_rechazo", 760, texto(operador.post("/usuarios/4/vehiculos", data={
        "placa": "ABC123", "marca": "Mazda", "color": "Blanco"}))))
    # HU-09: inactivación (baja lógica).
    capturas.append(("15_usuario_inactivado", 760, texto(operador.post("/usuarios/4/estado", data={
        "estado": "INACTIVO"}, follow_redirects=True))))

    # Datos para el mapa de celdas: dos vehículos dentro.
    operador.post("/entrada", data={"placa": "ABC123", "celda": "", "observacion": ""})
    operador.post("/entrada", data={"placa": "FGH45K", "celda": "", "observacion": ""})
    # HU-11 / HU-12: mapa de celdas en la vista del administrador, tras crear una celda.
    capturas.append(("16_celdas_admin", 900, texto(admin.post("/celdas", data={"codigo": "C-11"},
                                                                follow_redirects=True))))
    # HU-13: rechazo al intentar sacar de servicio una celda ocupada (RN-12).
    capturas.append(("17_celda_rechazo", 900, texto(admin.post("/celdas/1/estado", data={
        "estado": "FUERA_DE_SERVICIO"}, follow_redirects=True))))
    # HU-15: reubicación exitosa desde la vista del operador (sin acciones de administrador).
    capturas.append(("18_reubicacion_exito", 820, texto(operador.post("/celdas/reubicar", data={
        "placa": "ABC123", "destino": "C-04"}, follow_redirects=True))))
    # HU-15: rechazo de reubicación hacia una celda fuera de servicio (RN-03).
    capturas.append(("19_reubicacion_rechazo", 820, texto(operador.post("/celdas/reubicar", data={
        "placa": "ABC123", "destino": "C-10"}))))

    # --- Iteración 3: gestión de pagos -----------------------------------------------------------
    # El usuario 4 quedó inactivo en la HU-09; se reactiva para que pueda pagar (RN-18).
    operador.post("/usuarios/4/estado", data={"estado": "ACTIVO"})
    operador.get("/usuarios/4")  # consume el aviso de reactivación para que no aparezca en el mockup
    # HU-16: formulario de pago con la tarifa vigente y el recaudo del mes (captura).
    capturas.append(("20_pagos_registro", 900, texto(operador.get("/pagos?pagar=DEF456"))))
    # HU-16: rechazo por transferencia sin referencia (RN-17), conserva lo digitado.
    capturas.append(("21_pago_rechazo", 900, texto(operador.post("/pagos", data={
        "placa": "DEF456", "periodo": "2026-11", "medio": "TRANSFERENCIA", "referencia": ""}))))
    # HU-16: confirmación con el recibo imprimible.
    capturas.append(("22_recibo", 640, texto(operador.post("/pagos", data={
        "placa": "DEF456", "periodo": "2026-11", "medio": "TRANSFERENCIA", "referencia": "TRF-55021"},
        follow_redirects=True))))
    # HU-21: entrada rechazada por mensualidad pendiente (RN-19).
    capturas.append(("23_entrada_rechazo_mensualidad", 640, texto(operador.post("/entrada", data={
        "placa": "MNO12P", "celda": "", "observacion": ""}))))
    # HU-18: estado de cuenta en la ficha del usuario (un vehículo al día y otro pendiente).
    capturas.append(("24_estado_cuenta", 800, texto(operador.get("/usuarios/4"))))
    # HU-19: el administrador ve la opción de anular en el recibo.
    capturas.append(("25_recibo_admin_anular", 760, texto(admin.get("/pagos/13"))))
    # HU-19: pago anulado (RN-20): queda en el historial con su motivo.
    capturas.append(("26_pago_anulado", 700, texto(admin.post("/pagos/13/anular", data={
        "motivo": "El pago se registró a la placa equivocada"}, follow_redirects=True))))
    # HU-20: tarifas en la vista del administrador, tras actualizar la de motos.
    capturas.append(("27_tarifas_admin", 560, texto(admin.post("/tarifas", data={
        "tipo": "MOTO", "valor": "75000"}, follow_redirects=True))))
    return capturas


def capturar(navegador: str, html: Path, png: Path, alto: int, perfil: str) -> None:
    Path(perfil).mkdir(exist_ok=True)
    subprocess.run([
        navegador, "--headless", "--no-remote", "--profile", perfil,
        f"--window-size={ANCHO},{alto}", "--screenshot", str(png), html.as_uri(),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)


def main() -> None:
    navegador = sys.argv[1] if len(sys.argv) > 1 else shutil.which("firefox")
    if not navegador:
        sys.exit("No se encontró Firefox; indique la ruta del ejecutable como argumento.")
    carpeta_html = SALIDA / "html"
    carpeta_html.mkdir(exist_ok=True)
    # Firefox se ejecuta fuera de /tmp para evitar restricciones de sandbox en algunas distribuciones.
    with tempfile.TemporaryDirectory(dir=Path.home()) as tmp:
        app = create_app({"DATABASE": str(Path(tmp) / "mockups.db"), "TESTING": True})
        desde = os.environ.get("MOCKUPS_DESDE", "")
        for nombre, alto, html in pantallas(app):
            if desde and nombre[:2] < desde:
                continue
            ruta_html = carpeta_html / f"{nombre}.html"
            ruta_html.write_text(_autocontenido(html), encoding="utf-8")
            capturar(navegador, ruta_html, SALIDA / f"{nombre}.png", alto, str(Path(tmp) / "perfil"))
            print(f"{nombre}.png")


if __name__ == "__main__":
    main()
