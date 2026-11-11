
from archivos import cargar_reservas, cargar_indice, ruta_reservas, existe_archivo
from logica import (posiciones, validar_trayecto, tarifa_trayecto, precio_silla,
                    construir_matriz, contar_libres, formato_dinero, calcular_totales)
from operaciones import (evaluar_silla, armar_viaje, confirmar_transaccion, cancelar_transaccion,
                         lineas_tiquete, buscar_transacciones)
from reportes import lineas_manifiesto, generar_reporte, exportar_reporte
from validaciones import (validar_fecha, validar_pasajero, pedir, pedir_confirmacion, fechas_en_rango)



def val_servicio(texto, servicios):
    """Valida que el servicio exista."""
    sid = texto.strip().upper()
    if sid in servicios:
        return sid, ""
    return None, "El servicio no existe. Elija uno de la lista."


def val_fecha(texto, fecha_min):
    """Valida la fecha y, si se indica, que no sea anterior a fecha_min."""
    fecha, error = validar_fecha(texto)
    if fecha is None:
        return None, error
    if fecha_min is not None and fecha < fecha_min:
        return None, "La fecha no puede ser anterior a " + fecha_min + "."
    return fecha, ""


def val_parada(texto, paradas_ruta):
    """Valida que el código exista en la ruta."""
    codigo = texto.strip().upper()
    if codigo in paradas_ruta:
        return codigo, ""
    return None, "Parada inexistente. Opciones: " + ", ".join(paradas_ruta) + "."


def val_destino(texto, datos):
    """Valida el destino: debe existir y quedar después del origen."""
    paradas_ruta, origen = datos
    codigo = texto.strip().upper()
    i, j, error = validar_trayecto(paradas_ruta, origen, codigo)
    if i is None:
        return None, error
    return codigo, ""


def val_silla(texto, datos):
    """Valida formato y disponibilidad de la silla."""
    servicio, reservas, pos, i, j = datos
    silla, error = evaluar_silla(servicio, reservas, pos, i, j, texto)
    if silla is None:
        return None, error
    return texto, ""


def val_pasajero(texto, _):
    """Valida el identificador de pasajero."""
    return validar_pasajero(texto)


def val_parada_global(texto, ctx):
    """Valida que el código exista en alguna ruta."""
    codigo = texto.strip().upper()
    for ruta in ctx["paradas"]:
        if codigo in ctx["paradas"][ruta]:
            return codigo, ""
    return None, "Esa parada no existe en ninguna ruta."


def mostrar_menu():
    """Imprime el menú principal."""
    print("\n=============== RESERVAS INTERMUNICIPALES ===================")
    print("1.  Buscar servicio, fecha y recorrido")
    print("2. Ver mapa de asientos para un trayecto")
    print("3. Reservar viaje solo de ida")
    print("4 . Reservar ida y regreso en una transacción")
    print("5. Consultar tiquetes y cancelar transacción")
    print("6.  Consultar manifiesto por servicio y fecha")
    print("7. Analizar ocupación e ingresos por ruta y fechas")
    print("0. Guardar y salir")


def mostrar_servicios(ctx):
    """Lista los servicios disponibles con su ruta y hora."""
    print("Servicios disponibles:")
    for sid in sorted(ctx["servicios"]):
        s = ctx["servicios"][sid]
        print("  " + sid + " | ruta " + s["ruta"] + " (" + " -> ".join(ctx["paradas"][s["ruta"]])
              + ") | salida " + s["hora"])


def mostrar_matriz(servicio, matriz, sid, fecha, origen, destino):
    """Imprime el mapa de sillas de un trayecto (O libre, X no disponible)."""
    print("\nServicio " + sid + " | " + fecha + " | trayecto " + origen + "→" + destino)
    encabezado = "       "
    for c in range(servicio["columnas"]):
        encabezado += chr(65 + c) + "  "
    print(encabezado)
    for f in range(len(matriz)):
        clase = "PREMIUM" if f < servicio["filas_premium"] else "REGULAR"
        print("  F" + str(f + 1) + "   " + "  ".join(matriz[f]) + "   " + clase)
    print("  O = libre | X = no disponible (solo para este trayecto)")


def mostrar_resumen_viaje(titulo, v):
    """Imprime el resumen de un viaje antes de confirmar."""
    print("  " + titulo + ": " + v["sid"] + " " + v["fecha"] + " " + v["hora"] + " | "
          + v["origen"] + "→" + v["destino"] + " | silla " + v["silla"]["codigo"]
          + " (" + v["silla"]["clase"] + ") | pasajero " + v["pasajero"]
          + " | " + formato_dinero(v["precio"]))


def imprimir_lineas(lineas):
    """Imprime una lista de líneas de texto."""
    for linea in lineas:
        print(linea)


# Solicitud de un viaje

def solicitar_viaje(ctx, titulo, origen=None, destino=None, fecha_min=None):
    """Pide servicio, fecha, trayecto, silla y pasajero. Devuelve el viaje o None si cancela.

    Si origen y destino vienen fijos (regreso), solo se aceptan servicios que los cubran.
    """
    print("\n--- " + titulo + " ---")
    mostrar_servicios(ctx)
    while True:
        sid = pedir("Servicio", val_servicio, ctx["servicios"])
        if sid is None:
            return None
        servicio = ctx["servicios"][sid]
        paradas_ruta = ctx["paradas"][servicio["ruta"]]
        if origen is not None:
            i, j, error = validar_trayecto(paradas_ruta, origen, destino)
            if i is None:
                print("El servicio " + sid + " no cubre " + origen + "→" + destino + ". " + error)
                continue
            o, d = origen, destino
        else:
            o = pedir("Origen " + "/".join(paradas_ruta), val_parada, paradas_ruta)
            if o is None:
                return None
            d = pedir("Destino", val_destino, (paradas_ruta, o))
            if d is None:
                return None
            i, j, _ = validar_trayecto(paradas_ruta, o, d)
        break
    fecha = pedir("Fecha (AAAA-MM-DD)", val_fecha, fecha_min)
    if fecha is None:
        return None
    reservas = cargar_reservas(ctx["base"], sid, fecha, True)
    pos = posiciones(paradas_ruta)
    mostrar_matriz(servicio, construir_matriz(servicio, reservas, pos, i, j), sid, fecha, o, d)
    tarifa = tarifa_trayecto(ctx["tarifas"][servicio["ruta"]], i, j)
    print("Tarifa REGULAR " + formato_dinero(tarifa) + " | PREMIUM " + formato_dinero(precio_silla(tarifa, "PREMIUM")))
    silla = pedir("Silla (formatos «2A» o «F2 S A»)", val_silla, (servicio, reservas, pos, i, j))
    if silla is None:
        return None
    pasajero = pedir("Identificación del pasajero", val_pasajero)
    if pasajero is None:
        return None
    viaje, error = armar_viaje(ctx, sid, fecha, o, d, silla, pasajero)
    if viaje is None:
        print("  ✗ " + error)
    return viaje



def flujo_buscar(ctx):
    """Opción 1: busca servicios que cubren un recorrido en una fecha."""
    print("\n--- BUSCAR SERVICIO ---")
    origen = pedir("Origen", val_parada_global, ctx)
    if origen is None:
        return
    destino = pedir("Destino", val_parada_global, ctx)
    if destino is None:
        return
    fecha = pedir("Fecha (AAAA-MM-DD)", val_fecha, None)
    if fecha is None:
        return
    encontrados = 0
    for sid in sorted(ctx["servicios"]):
        servicio = ctx["servicios"][sid]
        paradas_ruta = ctx["paradas"][servicio["ruta"]]
        i, j, _ = validar_trayecto(paradas_ruta, origen, destino)
        if i is None:
            continue
        encontrados += 1
        reservas = cargar_reservas(ctx["base"], sid, fecha, True)
        matriz = construir_matriz(servicio, reservas, posiciones(paradas_ruta), i, j)
        tarifa = tarifa_trayecto(ctx["tarifas"][servicio["ruta"]], i, j)
        print("  " + sid + " | ruta " + servicio["ruta"] + " | salida " + servicio["hora"]
              + " | REGULAR " + formato_dinero(tarifa) + " | PREMIUM " + formato_dinero(precio_silla(tarifa, "PREMIUM"))
              + " | sillas libres: " + str(contar_libres(matriz)))
    if encontrados == 0:
        print("  No hay servicios que cubran " + origen + "->" + destino + ".")


def flujo_mapa(ctx):
    """Opción 2: muestra el mapa de sillas de un servicio, fecha y trayecto."""
    print("\n--- MAPA DE ASIENTOS ---")
    mostrar_servicios(ctx)
    sid = pedir("Servicio", val_servicio, ctx["servicios"])
    if sid is None:
        return
    servicio = ctx["servicios"][sid]
    paradas_ruta = ctx["paradas"][servicio["ruta"]]
    origen = pedir("Origen " + "/".join(paradas_ruta), val_parada, paradas_ruta)
    if origen is None:
        return
    destino = pedir("Destino", val_destino, (paradas_ruta, origen))
    if destino is None:
        return
    fecha = pedir("Fecha (AAAA-MM-DD)", val_fecha, None)
    if fecha is None:
        return
    i, j, _ = validar_trayecto(paradas_ruta, origen, destino)
    reservas = cargar_reservas(ctx["base"], sid, fecha, True)
    mostrar_matriz(servicio, construir_matriz(servicio, reservas, posiciones(paradas_ruta), i, j),
                   sid, fecha, origen, destino)


def flujo_ida(ctx):
    """Opción 3: reserva de solo ida."""
    viaje = solicitar_viaje(ctx, "RESERVA SOLO IDA")
    if viaje is None:
        print("Operación cancelada. No se guardó nada.")
        return
    print("\nResumen:")
    mostrar_resumen_viaje("IDA", viaje)
    if not pedir_confirmacion("¿Confirmar la reserva?"):
        print("Operación cancelada. No se guardó nada.")
        return
    tx, mensaje = confirmar_transaccion(ctx, [viaje])
    print(("bine " if tx is not None else "mal ") + mensaje)
    if tx is not None:
        imprimir_lineas(lineas_tiquete(ctx, tx, cargar_indice(ctx["base"])))


def flujo_ida_regreso(ctx):
    """Opción 4: reserva de ida y regreso como una sola transacción atómica."""
    ida = solicitar_viaje(ctx, "IDA")
    if ida is None:
        print("Operación cancelada. No se guardó nada.")
        return
    print("\nIda lista (aún sin guardar). Ahora el regreso " + ida["destino"] + "->" + ida["origen"] + ".")
    regreso = solicitar_viaje(ctx, "REGRESO", ida["destino"], ida["origen"], ida["fecha"])
    if regreso is None:
        print("Operación cancelada: no se guardó la ida ni se emitió tiquete.")
        return
    subtotal, descuento, total = calcular_totales([ida["precio"], regreso["precio"]])
    print("\nResumen:")
    mostrar_resumen_viaje("IDA    ", ida)
    mostrar_resumen_viaje("REGRESO", regreso)
    print("  Subtotal " + formato_dinero(subtotal) + " | Descuento 10 % " + formato_dinero(descuento)
          + " | Total " + formato_dinero(total))
    if not pedir_confirmacion("¿Confirmar la transacción?"):
        print("Operación cancelada. No se guardó nada.")
        return
    tx, mensaje = confirmar_transaccion(ctx, [ida, regreso])
    print(("bien " if tx is not None else "Mal ") + mensaje)
    if tx is not None:
        imprimir_lineas(lineas_tiquete(ctx, tx, cargar_indice(ctx["base"])))


def mostrar_busqueda(ctx, por, valor):
    """Muestra los tiquetes que coinciden con una transacción o pasajero."""
    encontradas = buscar_transacciones(ctx, por, valor)
    if len(encontradas) == 0:
        print("  No se encontraron transacciones.")
    indice = cargar_indice(ctx["base"])
    for tx in encontradas:
        imprimir_lineas(lineas_tiquete(ctx, tx, indice))


def val_texto_id(texto, _):
    """Valida un identificador no vacío en mayúsculas."""
    valor = texto.strip().upper()
    if valor == "":
        return None, "No puede estar vacío."
    return valor, ""


def flujo_tiquetes(ctx):
    """Opción 5: consulta tiquetes por transacción o pasajero y cancela transacciones."""
    while True:
        print("\n--- TIQUETES Y CANCELACIÓN ---")
        print("1. Consultar por transacción\n2. Consultar por pasajero\n3. Cancelar transacción\n0. Volver")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            valor = pedir("Código de transacción (ej: T001)", val_texto_id)
            if valor is not None:
                mostrar_busqueda(ctx, "transaccion", valor)
        elif opcion == "2":
            valor = pedir("Identificación del pasajero", val_pasajero)
            if valor is not None:
                mostrar_busqueda(ctx, "pasajero", valor)
        elif opcion == "3":
            valor = pedir("Transacción a cancelar", val_texto_id)
            if valor is not None:
                encontradas = buscar_transacciones(ctx, "transaccion", valor)
                if len(encontradas) == 0:
                    print("✗ La transacción no existe.")
                    continue
                imprimir_lineas(lineas_tiquete(ctx, encontradas[0], cargar_indice(ctx["base"])))
                if pedir_confirmacion("¿Cancelar esta transacción?"):
                    ok, mensaje = cancelar_transaccion(ctx, valor)
                    print(("Bien " if ok else "Mal ") + mensaje)
                else:
                    print("Cancelación abortada. No se cambió nada.")
        elif opcion == "0":
            return
        else:
            print(" Opción inválida.")


def flujo_manifiesto(ctx):
    """Opción 6: manifiesto de reservas ACTIVAS de un servicio y fecha."""
    print("\n--- MANIFIESTO ---")
    mostrar_servicios(ctx)
    sid = pedir("Servicio", val_servicio, ctx["servicios"])
    if sid is None:
        return
    fecha = pedir("Fecha (AAAA-MM-DD)", val_fecha, None)
    if fecha is None:
        return
    reservas = cargar_reservas(ctx["base"], sid, fecha, True)
    print("\nManifiesto " + sid + " | " + fecha + " | reservas ACTIVAS")
    lineas = lineas_manifiesto(reservas)
    if len(lineas) == 0:
        print("  (Sin reservas activas.)")
    imprimir_lineas(lineas)


def val_rango(texto, _):
    """Valida una fecha para el rango de análisis."""
    return validar_fecha(texto)


def flujo_analisis(ctx):
    """Opción 7: ocupación, ingresos y top 3 por ruta y rango de fechas; exporta archivos."""
    print("\n--- ANÁLISIS POR RUTA ---")
    rutas = []
    for sid in ctx["servicios"]:
        if ctx["servicios"][sid]["ruta"] not in rutas:
            rutas.append(ctx["servicios"][sid]["ruta"])
    rutas.sort()
    print("Rutas: " + ", ".join(rutas))
    ruta = pedir("Ruta", val_servicio, rutas_como_dict(rutas))
    if ruta is None:
        return
    inicio = pedir("Fecha inicial (AAAA-MM-DD)", val_rango)
    if inicio is None:
        return
    while True:
        final = pedir("Fecha final (AAAA-MM-DD)", val_rango)
        if final is None:
            return
        if final < inicio:
            print("  La fecha final no puede ser anterior a la inicial.")
        elif len(fechas_en_rango(inicio, final, 367)) > 366:
            print("El rango máximo es de 366 días.")
        else:
            break
    lineas, filas_csv, _ = generar_reporte(ctx, ruta, inicio, final)
    print()
    imprimir_lineas(lineas)
    corrida = exportar_reporte(ctx["base"], lineas, filas_csv)
    print("\n Corrida " + str(corrida) + " agregada a reporte_ruta.txt y ocupacion_tramos.csv.")


def rutas_como_dict(rutas):
    """Convierte la lista de rutas en un diccionario para reutilizar val_servicio."""
    d = {}
    for r in rutas:
        d[r] = True
    return d


def menu_principal(ctx):
    """Ciclo del menú principal: se mantiene hasta elegir 0 (salir)."""
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ").strip()
        try:
            if opcion == "1":
                flujo_buscar(ctx)
            elif opcion == "2":
                flujo_mapa(ctx)
            elif opcion == "3":
                flujo_ida(ctx)
            elif opcion == "4":
                flujo_ida_regreso(ctx)
            elif opcion == "5":
                flujo_tiquetes(ctx)
            elif opcion == "6":
                flujo_manifiesto(ctx)
            elif opcion == "7":
                flujo_analisis(ctx)
            elif opcion == "0":
                print("Todo quedó guardado en los archivos. ¡Hasta pronto!")
                return
            else:
                print("Opción inválida. Elija un número del menú.")
        except (OSError, ValueError) as error:
            print(" Problema con los archivos: " + str(error))
            print("  La operación no se completó; el menú sigue disponible.")
