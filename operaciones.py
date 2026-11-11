

from archivos import (cargar_reservas, guardar_reservas, cargar_transacciones,
                      guardar_transacciones, cargar_indice, agregar_filas,
                      registrar_movimiento, ubicar_reserva)
from logica import (posiciones, validar_trayecto, tarifa_trayecto, clase_de_fila,
                    precio_silla, calcular_totales, codigo_silla, buscar_conflicto,
                    formato_dinero)
from validaciones import validar_fecha, validar_pasajero, parsear_silla


def siguiente_numero(ids, prefijo):


    """Devuelve el siguiente número libre para ids como R001, T002, etc."""
    mayor = 0
    for identificador in ids:
        resto = identificador[len(prefijo):]
        if identificador.startswith(prefijo) and resto.isdigit():
            mayor = max(mayor, int(resto))
    return mayor + 1


def formar_id(prefijo, numero):
    """Construye un identificador como R007."""
    texto = str(numero)
    while len(texto) < 3:
        texto = "0" + texto
    return prefijo + texto



def evaluar_silla(servicio, reservas, pos, i, j, texto):


    """Valida formato, fila, columna y disponibilidad de una silla para [i, j).

    Devuelve (silla, "") con silla = {codigo, fila, col, clase} o (None, error).
    """
    indices, error = parsear_silla(texto, servicio["filas"], servicio["columnas"])


    if indices is None:
        return None, error
    codigo = codigo_silla(indices[0], indices[1])
    conflicto = buscar_conflicto(reservas, pos, codigo, i, j)


    if conflicto is not None:
        return None, ("La silla " + codigo + " no está disponible para este trayecto: se solapa con la reserva "
                      + conflicto["reserva_id"] + " (" + conflicto["origen"] + "→" + conflicto["destino"] + ").")
    clase = clase_de_fila(indices[0], servicio["filas_premium"])
    return {"codigo": codigo, "fila": indices[0], "col": indices[1], "clase": clase}, ""


def armar_viaje(ctx, sid, fecha, origen, destino, silla_texto, pasajero):

    """Valida todos los datos de un viaje y calcula su precio (no guarda nada).

    Devuelve (viaje, "") o (None, mensaje_error).
    """
    if sid not in ctx["servicios"]:
        return None, "El servicio " + sid + " no existe."
    
    fecha_ok, error = validar_fecha(fecha)


    if fecha_ok is None:
        return None, error
    servicio = ctx["servicios"][sid]
    ruta = servicio["ruta"]
    i, j, error = validar_trayecto(ctx["paradas"][ruta], origen, destino)


    if i is None:
        return None, error
    pasajero_ok, error = validar_pasajero(pasajero)
    if pasajero_ok is None:
        return None, error
    reservas = cargar_reservas(ctx["base"], sid, fecha, True)
    pos = posiciones(ctx["paradas"][ruta])
    silla, error = evaluar_silla(servicio, reservas, pos, i, j, silla_texto)



    if silla is None:
        return None, error
    tarifa = tarifa_trayecto(ctx["tarifas"][ruta], i, j)
    return {"sid": sid, "fecha": fecha, "ruta": ruta, "hora": servicio["hora"],
            "origen": origen, "destino": destino, "i": i, "j": j, "silla": silla,
            "pasajero": pasajero_ok, "tarifa": tarifa,
            "precio": precio_silla(tarifa, silla["clase"]), "reservas": reservas}, ""


def validar_pareja(ida, regreso):
    
    """Valida que regreso sea el viaje de vuelta de ida. Devuelve '' o un error."""
    if regreso["origen"] != ida["destino"] or regreso["destino"] != ida["origen"]:
        return "El regreso debe ir de " + ida["destino"] + " a " + ida["origen"] + "."

    
    if regreso["fecha"] < ida["fecha"]:
        return "La fecha de regreso no puede ser anterior a la de ida."
    
    if regreso["sid"] == ida["sid"] and regreso["fecha"] == ida["fecha"]:
        return "Ida y regreso no pueden ser el mismo servicio y fecha."
    
    return ""



def _restaurar(base, guardados):
    """Devuelve a su estado original los archivos de reservas ya reescritos."""

    for sid, fecha, originales in guardados:
        try:
            guardar_reservas(base, sid, fecha, originales)



        except OSError:
            print("   No se pudo restaurar " + sid + "_" + fecha + ".csv; revise el archivo.")


def confirmar_transaccion(ctx, viajes):
    """Confirma una transacción de 1 viaje (solo ida) o 2 viajes (ida y regreso).

    Es atómica: revalida todo con los archivos actuales y solo entonces escribe.
    Devuelve (transaccion, mensaje); transaccion es None si hubo rechazo o fallo.
    """
    base = ctx["base"]
    if len(viajes) == 2:
        error = validar_pareja(viajes[0], viajes[1])
        if error != "":
            return None, error

        
    for v in viajes:  # revalidación con el estado vigente en disco
        v["reservas"] = cargar_reservas(base, v["sid"], v["fecha"], True)
        pos = posiciones(ctx["paradas"][v["ruta"]])
        silla, error = evaluar_silla(ctx["servicios"][v["sid"]], v["reservas"], pos,
                                     v["i"], v["j"], v["silla"]["codigo"])

        
        if silla is None:
            return None, "Rechazado, no se guardó nada: " + error
    transacciones = cargar_transacciones(base)
    indice = cargar_indice(base)
    ids_reservas = list(indice.keys())
    for t in transacciones:
        ids_reservas.append(t["ida_reserva"])
        if t["regreso_reserva"] != "":
            ids_reservas.append(t["regreso_reserva"])
    n_res = siguiente_numero(ids_reservas, "R")
    tid = formar_id("T", siguiente_numero([t["transaccion_id"] for t in transacciones], "T"))
    nuevas = []
    for k in range(len(viajes)):
        v = viajes[k]
        nuevas.append({"reserva_id": formar_id("R", n_res + k), "pasajero_id": v["pasajero"],
                       "silla": v["silla"]["codigo"], "origen": v["origen"], "destino": v["destino"],
                       "precio": v["precio"], "estado": "ACTIVA", "transaccion_id": tid})
    subtotal, descuento, total = calcular_totales([v["precio"] for v in viajes])
    regreso_id = ""


    if len(viajes) == 2:
        regreso_id = nuevas[1]["reserva_id"]
    tx = {"transaccion_id": tid, "fecha": viajes[0]["fecha"], "ida_reserva": nuevas[0]["reserva_id"],
          "regreso_reserva": regreso_id, "subtotal": subtotal, "descuento": descuento,
          "total": total, "estado": "ACTIVA"}
    guardados = []


    try:

        for k in range(len(viajes)):
            v = viajes[k]
            guardar_reservas(base, v["sid"], v["fecha"], v["reservas"] + [nuevas[k]])
            guardados.append((v["sid"], v["fecha"], v["reservas"]))
        filas_indice = []
        for k in range(len(viajes)):
            filas_indice.append([nuevas[k]["reserva_id"], viajes[k]["sid"], viajes[k]["fecha"]])
        agregar_filas(base + "indice_reservas.csv", filas_indice)
        guardar_transacciones(base, transacciones + [tx])
    except OSError as error:
        _restaurar(base, guardados)
        return None, "No se pudo guardar (" + str(error) + "). Se restauró el estado anterior."
    try:
        tipo = "RESERVA_IDA"



        if len(viajes) == 2:
            tipo = "RESERVA_IDA_REGRESO"
        detalle = ""
        for k in range(len(viajes)):
            detalle += (viajes[k]["sid"] + " " + viajes[k]["fecha"] + " " + nuevas[k]["silla"] + " "
                        + viajes[k]["origen"] + "->" + viajes[k]["destino"] + " ")
        registrar_movimiento(base, tipo, tid, detalle.strip() + " total " + str(total))
    except OSError:
        print("  La transacción quedó guardada, pero no se pudo escribir movimientos.csv.")
    return tx, "Transacción " + tid + " confirmada. Total: " + formato_dinero(total) + "."


def reservas_de_transaccion(ctx, tx, indice):
    """Devuelve (lista_de_archivos, error) con las reservas de una transacción.

    Cada elemento: {sid, fecha, reservas (lista completa del archivo), reserva_id}.
    """
    resultado = []
    ids = [tx["ida_reserva"]]
    if tx["regreso_reserva"] != "":
        ids.append(tx["regreso_reserva"])
    cache = {}
    for rid in ids:
        lugar = ubicar_reserva(ctx, indice, rid, tx["fecha"])
        if lugar is None:
            return [], "No se encontró el archivo de la reserva " + rid + "."
        clave = lugar[0] + "_" + lugar[1]
        if clave not in cache:
            cache[clave] = cargar_reservas(ctx["base"], lugar[0], lugar[1], False)
        resultado.append({"sid": lugar[0], "fecha": lugar[1],
                          "reservas": cache[clave], "reserva_id": rid})
    return resultado, ""


def cancelar_transaccion(ctx, transaccion_id):
    """Cancela una transacción ACTIVA: reservas y transacción pasan a CANCELADA.

    No borra nada. Devuelve (True/False, mensaje).
    """
    base = ctx["base"]
    transacciones = cargar_transacciones(base)
    tx = None
    for t in transacciones:
        if t["transaccion_id"] == transaccion_id:
            tx = t
    if tx is None:
        return False, "La transacción " + transaccion_id + " no existe."
    if tx["estado"] != "ACTIVA":
        return False, "Transición no permitida: la transacción ya está " + tx["estado"] + "."
    partes, error = reservas_de_transaccion(ctx, tx, cargar_indice(base))
    if error != "":
        return False, error + " No se modificó nada."
    originales = {}
    for p in partes:  # copias para poder restaurar
        clave = p["sid"] + "_" + p["fecha"]
        if clave not in originales:
            copia = []
            for r in p["reservas"]:
                copia.append(dict(r))
            originales[clave] = (p["sid"], p["fecha"], copia)
    for p in partes:
        for r in p["reservas"]:
            if r["reserva_id"] == p["reserva_id"] and r["transaccion_id"] == tx["transaccion_id"]:
                r["estado"] = "CANCELADA"
    guardados = []
    try:
        escritos = []
        for p in partes:
            clave = p["sid"] + "_" + p["fecha"]
            if clave not in escritos:
                guardar_reservas(base, p["sid"], p["fecha"], p["reservas"])
                escritos.append(clave)
                guardados.append(originales[clave])
        tx["estado"] = "CANCELADA"
        guardar_transacciones(base, transacciones)
    except OSError as error:
        _restaurar(base, guardados)
        return False, "No se pudo cancelar (" + str(error) + "). Se restauró el estado anterior."
    try:
        registrar_movimiento(base, "CANCELACION", transaccion_id, "Reservas canceladas; sillas liberadas")
    except OSError:
        print("  ⚠ Cancelación guardada, pero no se pudo escribir movimientos.csv.")
    return True, "Transacción " + transaccion_id + " cancelada. Las sillas quedaron libres."


def lineas_tiquete(ctx, tx, indice):
    """Construye las líneas de texto del tiquete de una transacción."""
    lineas = ["Transacción " + tx["transaccion_id"] + " | " + tx["estado"] + " | fecha " + tx["fecha"],
              "  Subtotal " + formato_dinero(tx["subtotal"]) + " | Descuento "
              + formato_dinero(tx["descuento"]) + " | Total " + formato_dinero(tx["total"])]
    partes, error = reservas_de_transaccion(ctx, tx, indice)
    if error != "":
        lineas.append(error)
        return lineas
    etiquetas = ["IDA    ", "REGRESO"]
    for k in range(len(partes)):
        p = partes[k]
        for r in p["reservas"]:
            if r["reserva_id"] == p["reserva_id"]:
                hora = ctx["servicios"][p["sid"]]["hora"]
                lineas.append("  " + etiquetas[k] + " " + r["reserva_id"] + " | " + p["sid"] + " " + p["fecha"]
                              + " " + hora + " | " + r["origen"] + "→" + r["destino"] + " | silla "
                              + r["silla"] + " | pasajero " + r["pasajero_id"] + " | "
                              + formato_dinero(r["precio"]) + " | " + r["estado"])
    return lineas


def buscar_transacciones(ctx, por, valor):
    """Busca transacciones por 'transaccion' (id) o por 'pasajero' (id de pasajero)."""
    base = ctx["base"]
    transacciones = cargar_transacciones(base)
    if por == "transaccion":
        encontradas = []
        for t in transacciones:
            if t["transaccion_id"] == valor:
                encontradas.append(t)
        return encontradas
    indice = cargar_indice(base)
    encontradas = []
    for t in transacciones:
        partes, error = reservas_de_transaccion(ctx, t, indice)
        for p in partes:
            for r in p["reservas"]:
                if r["reserva_id"] == p["reserva_id"] and r["pasajero_id"] == valor \
                        and t not in encontradas:
                    encontradas.append(t)
    return encontradas
