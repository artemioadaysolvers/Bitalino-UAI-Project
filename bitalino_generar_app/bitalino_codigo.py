import csv
import sys
from pathlib import Path

ES_EXE = getattr(sys, "frozen", False)

def compilar():
    from importlib.util import find_spec
    from subprocess import run

    carpeta = Path(__file__).resolve().parent
    if any(find_spec(modulo) is None for modulo in ("bitalino", "webview", "PyInstaller")):
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
             "pyinstaller==6.22.3"], cwd=carpeta, check=True)

    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
         "--name", "Bitalino", "--add-data", "visualizador.html:.", "--collect-all",
         "webview", Path(__file__).name], cwd=carpeta, check=True)


if __name__ == "__main__" and not ES_EXE:
    from argparse import ArgumentParser

    terminal = ArgumentParser(description="Genera dist/Bitalino.exe por defecto.")
    terminal.add_argument("--app", action="store_true", help="Abre la app desde Python.")
    if not terminal.parse_args().app:
        compilar()
        raise SystemExit

import bitalino
import webview


# Configuración del BITalino: igual que en el cuaderno.
PUERTO = "COM6"
CANAL = 0  # A1 = 0, A2 = 1, A3 = 2, etc.
PERIODO = 0.01
N = 10
DURACION = 10

SENAL = "ECG"  # Cambia a "EMG" o "EDA" para otra captura.

titulo_grafico = f"Serie temporal del {SENAL}"
etiqueta_eje_y = SENAL
ruta_programa = Path(sys.executable if ES_EXE else __file__)
archivo_csv = ruta_programa.resolve().with_name(f"{SENAL}_100s.csv")

with open(Path(__file__).with_name("visualizador.html"), encoding="utf-8") as archivo:
    Visualizador_HTML = archivo.read()

Visualizador_HTML_Inicial = (
    Visualizador_HTML
    .replace("__DURACION__", str(DURACION))
    .replace("__TITULO__", titulo_grafico)
    .replace("__ETIQUETA_EJE_Y__", etiqueta_eje_y)
)

datos_ram = []


def capturar():
    # Esperamos al gráfico antes de enviarle las muestras.
    while not ventana.events.loaded.wait(0.1):
        if ventana.events.closed.is_set():
            return
    if ventana.events.closed.is_set():
        return

    device = None
    n_medicion = 0

    try:
        device = bitalino.BITalino(PUERTO)

        with open(archivo_csv, "w", newline="", encoding="utf-8") as archivo:
            escritor_csv = csv.writer(archivo)
            escritor_csv.writerow(["Tiempo (s)", "Magnitud"])

            device.start(1 / PERIODO, [CANAL])
            N_mediciones_totales = int(DURACION / PERIODO)

            while n_medicion < N_mediciones_totales and not ventana.events.closed.is_set():
                cantidad = min(N, N_mediciones_totales - n_medicion)
                mediciones_bloque = []

                for muestra in device.read(cantidad):
                    n_medicion += 1
                    tiempo = n_medicion * PERIODO
                    valor = float(muestra[5])

                    mediciones_bloque.append([tiempo, valor])
                    escritor_csv.writerow([tiempo, valor])

                archivo.flush()
                datos_ram.extend(mediciones_bloque)

                # pywebview envía el bloque al visualizador.
                if not ventana.events.closed.is_set():
                    ventana.state.muestras = mediciones_bloque

    except Exception as error:
        mensaje = f"Captura interrumpida: {error}"
        print(mensaje)
        if not ventana.events.closed.is_set():
            ventana.state.errorCaptura = mensaje
    finally:
        if device is not None:
            device.close()


if __name__ == "__main__":
    # Sustituye display(HTML(...)).
    ventana = webview.create_window(
        titulo_grafico, html=Visualizador_HTML_Inicial, width=1020, height=500
    )
    # pywebview ejecuta capturar en otro hilo para que la ventana responda.
    webview.start(capturar, gui="edgechromium")
