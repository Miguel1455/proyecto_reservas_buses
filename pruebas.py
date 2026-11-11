from archivos import (cargar_contexto, cargar_reservas, cargar_transacciones, escribir_csv,
                      ENC_RESERVAS, ENC_TRANSACCIONES, ENC_INDICE, ENC_MOVIMIENTOS, ENC_OCUPACION)
from logica import tarifa_trayecto, precio_silla, validar_trayecto
from operaciones import armar_viaje, confirmar_transaccion, cancelar_transaccion
from reportes import generar_reporte
from validaciones import validar_fecha, parsear_silla

BASE = "datos_prueba/"
resultados = []


def reiniciar_datos():
    """Deja datos_prueba/ en el estado semilla (solo estos archivos cambian en las pruebas)."""
    escribir_csv(BASE + "transacciones.csv", ENC_TRANSACCIONES,
                 [["T001", "2026-11-12", "R001", "", "20000", "0", "20000", "ACTIVA"]])
    escribir_csv(BASE + "indice_reservas.csv", ENC_INDICE, [["R001", "B001", "2026-11-12"]])
    escribir_csv(BASE + "movimientos.csv", ENC_MOVIMIENTOS, [["1", "RESERVA_IDA", "T001", "semilla"]])
    escribir_csv(BASE + "ocupacion_tramos.csv", ENC_OCUPACION, [])
    archivo = open(BASE + "reporte_ruta.txt", "w", encoding="utf-8")
    archivo.write("")
    archivo.close()
    escribir_csv(BASE + "reservas/B001_2026-11-12.csv", ENC_RESERVAS,
                 [["R001", "C01", "2A", "MED", "RIO", "20000", "ACTIVA", "T001"]])
    for nombre in ["B001_2026-11-13", "B002_2026-11-12", "B002_2026-11-13", "B002_2026-11-14"]:
        escribir_csv(BASE + "reservas/" + nombre + ".csv", ENC_RESERVAS, [])


def verificar(nombre, condicion):
    """Registra e imprime el resultado de una prueba."""
    resultados.append(condicion)
    print(("PASA  " if condicion else "FALLA ") + nombre)


def reservar(ctx, sid, fecha, o, d, silla, pas):
    """Atajo: arma y confirma una reserva de solo ida. Devuelve (tx, mensaje)."""
    viaje, error = armar_viaje(ctx, sid, fecha, o, d, silla, pas)
    if viaje is None:
        return None, error
    return confirmar_transaccion(ctx, [viaje])


def main():
    """Ejecuta las pruebas de aceptación del Tema 5 y las transversales."""
    reiniciar_datos()
    ctx, avisos = cargar_contexto(BASE)
    verificar("Carga inicial real (servicios, rutas y tarifas)",
              len(ctx["servicios"]) == 2 and len(avisos) == 0 and ctx["tarifas"]["R1"] == [20000, 30000, 20000])

    tx, _ = reservar(ctx, "B001", "2026-11-12", "RIO", "BOG", "2A", "C02")
    verificar("1. Reutilización legal: MED→RIO y RIO → BOG coexisten en 2A", tx is not None)
    antes = cargar_reservas(BASE, "B001", "2026-11-12", False)
    tx, _ = reservar(ctx, "B001", "2026-11-12", "MED", "MAR", "2A", "C03")
    despues = cargar_reservas(BASE, "B001", "2026-11-12", False)
    verificar("2. Solapamiento bloqueado: MED→MAR rechazado en 2A y sin cambios en archivo",
              tx is None and antes == despues and len(despues) == 2)

    i, j, _ = validar_trayecto(ctx["paradas"]["R1"], "MED", "MAR")
    t = tarifa_trayecto(ctx["tarifas"]["R1"], i, j)
    verificar("3. Precio por sumatoria:  REGULAR 50.000 y PREMIUM 75.000",
              t == 50000 and precio_silla(t, "PREMIUM") == 75000)

    ida, _ = armar_viaje(ctx, "B001", "2026-11-12", "MED", "MAR", "2B", "C04")
    reg, _ = armar_viaje(ctx, "B002", "2026-11-13", "MAR", "MED", "2B", "C04")
    tx, _ = confirmar_transaccion(ctx, [ida, reg])
    verificar("4. Ida y vuelta: subtotal 100.000, descuento 10.000, total 90.000",
              tx is not None and tx["subtotal"] == 100000 and tx["descuento"] == 10000 and tx["total"] == 90000)

    reservar(ctx, "B002", "2026-11-14", "MAR", "MED", "2B", "C05")
    n_tx = len(cargar_transacciones(BASE))
    n_ida = len(cargar_reservas(BASE, "B001", "2026-11-14", True))
    ida, _ = armar_viaje(ctx, "B001", "2026-11-14", "MED", "MAR", "2B", "C06")
    reg, error = armar_viaje(ctx, "B002", "2026-11-14", "MAR", "MED", "2B", "C06")
    verificar("5. Atomicidad: regreso 2B ocupado -> no hay ida ni tiquete",
              ida is not None and reg is None and n_tx == len(cargar_transacciones(BASE))
              and n_ida == len(cargar_reservas(BASE, "B001", "2026-11-14", True)) == 0)

    reservar(ctx, "B001", "2026-11-12", "MED", "BOG", "3C", "C07")
    viaje13, _ = armar_viaje(ctx, "B001", "2026-11-13", "MED", "BOG", "3C", "C08")
    verificar("6. Persistencia temporal: 3C ocupada el 12 pero libre el 13 (archivos distintos)",
              viaje13 is not None)

    ctx2, _ = cargar_contexto(BASE)  # simula cerrar y volver a abrir
    res12 = cargar_reservas(BASE, "B001", "2026-11-12", False)
    verificar("7. Reinicio: se recuperan 4 reservas del 12 sin duplicar y 5 transacciones",
              len(res12) == 4 and len(cargar_transacciones(BASE)) == 5)

    ok, _ = cancelar_transaccion(ctx2, "T002")  # la de RIO→BOG en 2A
    libre, _ = armar_viaje(ctx2, "B001", "2026-11-12", "RIO", "BOG", "2A", "C09")
    estados = []
    for r in cargar_reservas(BASE, "B001", "2026-11-12", False):
        estados.append(r["estado"])
    verificar("8. Cancelación: reserva queda CANCELADA (no se borra) y la silla se libera",
              ok and "CANCELADA" in estados and len(estados) == 4 and libre is not None)
    ok2, _ = cancelar_transaccion(ctx2, "T002")
    verificar("9. Transición prohibida: no se puede cancelar dos veces", not ok2)

    verificar("10. Errores controlados: fecha 2026-02-30, silla 9Z y destino anterior al origen",
              validar_fecha("2026-02-30")[0] is None and parsear_silla("9Z", 4, 4)[0] is None
              and validar_trayecto(ctx["paradas"]["R1"], "BOG", "MED")[0] is None)

    lineas, filas, _ = generar_reporte(ctx2, "R1", "2026-11-12", "2026-11-14")
    verificar("11. Reporte: ingresos solo de transacciones ACTIVAS", any("Transacciones ACTIVAS" in l for l in lineas))
    print("\n" + str(sum(resultados)) + " de " + str(len(resultados)) + " pruebas pasaron.")


main()
