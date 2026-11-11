"""Punto de entrada: python main.py"""

from archivos import cargar_contexto, informar_avisos
from consola import menu_principal

CARPETA_DATOS = "datos/"

try:
    ctx, avisos = cargar_contexto(CARPETA_DATOS)
except (OSError, ValueError) as error:
    print(" No se pudo iniciar: " + str(error))
    print("  Verifique que existan servicios.csv, paradas.csv y tramos.csv en " + CARPETA_DATOS)
else:
    print("Datos cargados desde " + CARPETA_DATOS)
    informar_avisos(avisos)
    try:
        menu_principal(ctx)
    except (EOFError, KeyboardInterrupt):
        print("\nEntrada finalizada. Los datos ya estaban guardados.")
