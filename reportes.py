"""Reportes: manifiesto, ocupación por tramo, ingresos y top 3 de trayectos."""

from archivos import (cargar_reservas, cargar_transacciones, cargar_indice, existe_archivo,
                      ruta_reservas, ubicar_reserva, leer_csv, asegurar_archivo,
                      agregar_filas, ENC_OCUPACION)
from logica import posiciones, ocupacion_por_tramo, pico_ocupacion, formato_dinero
from validaciones import fechas_en_rango


def lineas_manifiesto(reservas):
    """Líneas del manifiesto: solo reservas ACTIVAS, ordenadas por silla."""
    activas = []
    for r in reservas:
        if r["estado"] == "ACTIVA":
            clave = r["silla"]
            if len(clave) < 3:
                clave = "0" + clave
            linea = ("  Silla " + r["silla"] + " | pasajero " + r["pasajero_id"] + " | "
                     + r["origen"] + "→" + r["destino"] + " | " + r["reserva_id"])
            activas.append((clave, r["reserva_id"], linea))
    activas.sort()
    lineas = []
    for _, _, linea in activas:
        lineas.append(linea)
    return lineas


def porcentaje(ocupadas, capacidad):
    """Devuelve el porcentaje de ocupación como texto con un decimal."""
    return format(100 * ocupadas / capacidad, ".1f")


def generar_reporte(ctx, ruta, fecha_inicial, fecha_final):
    """Calcula el reporte de una ruta en un rango de fechas.

    Devuelve (lineas_de_texto, filas_csv, avisos). Solo lee archivos existentes.
    """
    base = ctx["base"]
    paradas = ctx["paradas"][ruta]
    pos = posiciones(paradas)
    fechas = fechas_en_rango(fecha_inicial, fecha_final)
    servicios_ruta = []
    for sid in sorted(ctx["servicios"]):
        if ctx["servicios"][sid]["ruta"] == ruta:
            servicios_ruta.append(sid)
    lineas = ["REPORTE DE RUTA " + ruta + " (" + "-".join(paradas) + ") | " + fecha_inicial + " a " + fecha_final,
              "", "--- Ocupación por tramo (sillas ocupadas / capacidad) ---"]
    filas_csv = []
    conteo = {}
    pico_global = (-1, "", "")
    sin_datos = True
    for fecha in fechas:
        for sid in servicios_ruta:
            if not existe_archivo(ruta_reservas(base, sid, fecha)):
                continue
            sin_datos = False
            servicio = ctx["servicios"][sid]
            capacidad = servicio["filas"] * servicio["columnas"]
            reservas = cargar_reservas(base, sid, fecha, False)
            ocupadas = ocupacion_por_tramo(reservas, pos, len(paradas))
            lineas.append(sid + " | " + fecha + " | salida " + servicio["hora"])
            for k in range(len(ocupadas)):
                tramo = paradas[k] + "→" + paradas[k + 1]
                lineas.append("  " + tramo + ": " + str(ocupadas[k]) + "/" + str(capacidad)
                              + " (" + porcentaje(ocupadas[k], capacidad) + " %)")
                filas_csv.append([sid, fecha, str(k + 1), paradas[k], paradas[k + 1],
                                  str(ocupadas[k]), str(capacidad), porcentaje(ocupadas[k], capacidad)])
            maximo, k = pico_ocupacion(ocupadas)
            lineas.append("  Pico: " + str(maximo) + "/" + str(capacidad) + " en " + paradas[k] + "→" + paradas[k + 1])
            if maximo > pico_global[0]:
                pico_global = (maximo, sid + " " + fecha, paradas[k] + "→" + paradas[k + 1])
            for r in reservas:
                if r["estado"] == "ACTIVA":
                    nombre = r["origen"] + "→" + r["destino"]
                    conteo[nombre] = conteo.get(nombre, 0) + 1
    if sin_datos:
        lineas.append("  (No hay archivos de reservas para esa ruta en ese rango.)")
    else:
        lineas.append("Pico global: " + str(pico_global[0]) + " sillas en " + pico_global[1] + ", tramo " + pico_global[2])
    ingreso, cantidad = calcular_ingresos(ctx, ruta, fecha_inicial, fecha_final)
    lineas += ["", "--- Ingresos activos (por transacción; ruta = ruta del viaje de ida) ---",
               "Transacciones ACTIVAS: " + str(cantidad) + " | Total: " + formato_dinero(ingreso),
               "", "--- Top 3 trayectos por pasajeros (empate: orden alfabético) ---"]
    ranking = []
    for nombre in conteo:
        ranking.append((-conteo[nombre], nombre))
    ranking.sort()
    if len(ranking) == 0:
        lineas.append("  (Sin pasajeros activos.)")
    for k in range(min(3, len(ranking))):
        lineas.append("  " + str(k + 1) + ". " + ranking[k][1] + " — " + str(-ranking[k][0]) + " pasajeros")
    return lineas, filas_csv, []


def calcular_ingresos(ctx, ruta, fecha_inicial, fecha_final):
    """Suma el total de transacciones ACTIVAS de la ruta y rango. Devuelve (total, cantidad).

    Cada transacción se cuenta una sola vez (no por reserva) y se asigna a la ruta
    del viaje de ida; su fecha es la fecha de la transacción.
    """
    base = ctx["base"]
    indice = cargar_indice(base)
    total = 0
    cantidad = 0
    for t in cargar_transacciones(base):
        if t["estado"] != "ACTIVA" or t["fecha"] < fecha_inicial or t["fecha"] > fecha_final:
            continue
        lugar = ubicar_reserva(ctx, indice, t["ida_reserva"], t["fecha"])
        if lugar is not None and ctx["servicios"][lugar[0]]["ruta"] == ruta:
            total += t["total"]
            cantidad += 1
    return total, cantidad


def exportar_reporte(base, lineas, filas_csv):
    """Agrega el reporte a reporte_ruta.txt y ocupacion_tramos.csv sin borrar historia.

    Devuelve el número de corrida asignado.
    """
    ruta_csv = base + "ocupacion_tramos.csv"
    asegurar_archivo(ruta_csv, ENC_OCUPACION)
    existentes, _ = leer_csv(ruta_csv, ENC_OCUPACION)
    corrida = 0
    for fila in existentes:
        if fila[0].isdigit():
            corrida = max(corrida, int(fila[0]))
    corrida += 1
    nuevas = []
    for fila in filas_csv:
        nuevas.append([str(corrida)] + fila)
    agregar_filas(ruta_csv, nuevas)
    archivo = open(base + "reporte_ruta.txt", "a", encoding="utf-8")
    archivo.write("===== CORRIDA " + str(corrida) + " =====\n")
    for linea in lineas:
        archivo.write(linea + "\n")
    archivo.write("\n")
    archivo.close()
    return corrida
