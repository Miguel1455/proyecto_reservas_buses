"""Lectura y escritura de archivos CSV/texto. No usa librerías externas."""

from validaciones import validar_hora

ENC_SERVICIOS = "servicio_id,ruta,hora,filas,columnas,filas_premium"
ENC_PARADAS = "ruta,posicion,codigo"
ENC_TRAMOS = "ruta,origen,destino,tarifa_regular"
ENC_RESERVAS = "reserva_id,pasajero_id,silla,origen,destino,precio,estado,transaccion_id"
ENC_TRANSACCIONES = "transaccion_id,fecha,ida_reserva,regreso_reserva,subtotal,descuento,total,estado"
ENC_INDICE = "reserva_id,servicio_id,fecha"
ENC_MOVIMIENTOS = "mov_id,tipo,transaccion_id,detalle"
ENC_OCUPACION = "corrida,servicio_id,fecha,tramo,origen,destino,ocupadas,capacidad,porcentaje"
ESTADOS = ["ACTIVA", "CANCELADA"]


# ----------------------------------------------------------------------
# Lectura / escritura genérica
# ----------------------------------------------------------------------
def informar_avisos(avisos):
    """Imprime los avisos de filas inválidas encontradas al leer archivos."""
    for aviso in avisos:
        print(aviso)


def existe_archivo(ruta):
    """Devuelve True si el archivo existe y se puede abrir."""
    try:
        archivo = open(ruta, "r", encoding="utf-8")
        archivo.close()
        return True
    except FileNotFoundError:
        return False


def leer_csv(ruta, encabezado):
    """Lee un CSV y devuelve (filas, avisos).

    Lanza FileNotFoundError si no existe y ValueError si el encabezado no coincide.
    Las filas mal formadas se ignoran y se reportan en avisos.
    """
    archivo = open(ruta, "r", encoding="utf-8")
    lineas = archivo.read().splitlines()
    archivo.close()
    if len(lineas) > 0:
        lineas[0] = lineas[0].replace("\ufeff", "")
    if len(lineas) == 0 or lineas[0].strip() != encabezado:
        raise ValueError("Encabezado inválido o ausente en " + ruta)
    cantidad = len(encabezado.split(","))
    filas = []
    avisos = []
    for numero in range(1, len(lineas)):
        if lineas[numero].strip() == "":
            continue
        campos = lineas[numero].split(",")
        for k in range(len(campos)):
            campos[k] = campos[k].strip()
        if len(campos) != cantidad:
            avisos.append(ruta + " línea " + str(numero + 1)
                          + ": se esperaban " + str(cantidad) + " campos; fila ignorada.")
        else:
            filas.append(campos)
    return filas, avisos


def escribir_csv(ruta, encabezado, filas):
    """Escribe el CSV completo (encabezado + filas). Lanza OSError si falla."""
    texto = encabezado + "\n"
    for fila in filas:
        texto += ",".join(fila) + "\n"
    archivo = open(ruta, "w", encoding="utf-8", newline="")
    archivo.write(texto)
    archivo.close()


def agregar_filas(ruta, filas):
    """Agrega filas al final de un CSV existente (no borra lo anterior)."""
    archivo = open(ruta, "a", encoding="utf-8", newline="")
    for fila in filas:
        archivo.write(",".join(fila) + "\n")
    archivo.close()



def asegurar_archivo(ruta, encabezado):
    """Crea el archivo con su encabezado si todavía no existe."""
    if not existe_archivo(ruta):
        escribir_csv(ruta, encabezado, [])



def cargar_servicios(base):
    """Lee servicios.csv. Devuelve ({servicio_id: datos}, avisos)."""
    filas, avisos = leer_csv(base + "servicios.csv", ENC_SERVICIOS)
    servicios = {}
    for sid, ruta, hora, n_filas, n_cols, n_prem in filas:
        if sid in servicios:
            avisos.append("servicios.csv: servicio " + sid + " repetido; se ignora.")
            continue
        if not (n_filas.isdigit() and n_cols.isdigit() and n_prem.isdigit()):
            avisos.append("servicios.csv: servicio " + sid + " con números inválidos; se ignora.")
            continue
        n_filas, n_cols, n_prem = int(n_filas), int(n_cols), int(n_prem)
        if n_filas < 1 or n_cols < 1 or n_cols > 26 or n_prem > n_filas:
            avisos.append("servicios.csv: servicio " + sid + " con configuración imposible; se ignora.")
            continue
        if validar_hora(hora)[0] is None:
            avisos.append("servicios.csv: servicio " + sid + " con hora inválida; se ignora.")
            continue
        servicios[sid] = {"ruta": ruta, "hora": hora, "filas": n_filas,
                          "columnas": n_cols, "filas_premium": n_prem}
    return servicios, avisos


def cargar_paradas(base):
    """Lee paradas.csv. Devuelve ({ruta: [codigos en orden]}, avisos)."""
    filas, avisos = leer_csv(base + "paradas.csv", ENC_PARADAS)
    temporal = {}
    for ruta, posicion, codigo in filas:
        if not posicion.isdigit() or codigo == "":
            avisos.append("paradas.csv: fila inválida en ruta " + ruta + "; se ignora.")
            continue
        if ruta not in temporal:
            temporal[ruta] = {}
        if int(posicion) in temporal[ruta]:
            avisos.append("paradas.csv: posición " + posicion + " repetida en " + ruta + ".")
            continue
        temporal[ruta][int(posicion)] = codigo
    paradas = {}
    for ruta in temporal:
        mapa = temporal[ruta]
        n = len(mapa)
        lista = []
        for p in range(n):
            if p in mapa:
                lista.append(mapa[p])
        if n < 2 or len(lista) != n or len(set(lista)) != n:
            avisos.append("paradas.csv: la ruta " + ruta + " es inconsistente; se ignora.")
        else:
            paradas[ruta] = lista
    return paradas, avisos


def cargar_tarifas(base, paradas):
    """Lee tramos.csv. Devuelve ({ruta: [tarifa del tramo 0, 1, ...]}, avisos)."""
    filas, avisos = leer_csv(base + "tramos.csv", ENC_TRAMOS)
    por_tramo = {}
    for ruta, origen, destino, tarifa in filas:
        if ruta not in paradas or not tarifa.isdigit() or int(tarifa) <= 0:
            avisos.append("tramos.csv: fila inválida (" + ruta + " " + origen + "-" + destino + "); se ignora.")
            continue
        lista = paradas[ruta]
        if origen not in lista or destino not in lista \
                or lista.index(destino) != lista.index(origen) + 1:
            avisos.append("tramos.csv: " + origen + "-" + destino + " no es un tramo consecutivo de " + ruta + ".")
            continue
        por_tramo[(ruta, lista.index(origen))] = int(tarifa)
    tarifas = {}
    for ruta in paradas:
        valores = []
        completa = True
        for k in range(len(paradas[ruta]) - 1):
            if (ruta, k) in por_tramo:
                valores.append(por_tramo[(ruta, k)])
            else:
                completa = False
        if completa:
            tarifas[ruta] = valores
        else:
            avisos.append("tramos.csv: faltan tarifas en la ruta " + ruta + "; no estará disponible.")
    return tarifas, avisos


def cargar_contexto(base):
    """Carga y valida todos los archivos de configuración.

    Devuelve (ctx, avisos) donde ctx es un diccionario con base, servicios,
    paradas y tarifas. Lanza FileNotFoundError / ValueError si no se puede operar.
    """
    servicios, a1 = cargar_servicios(base)
    paradas, a2 = cargar_paradas(base)
    tarifas, a3 = cargar_tarifas(base, paradas)
    avisos = a1 + a2 + a3
    validos = {}
    for sid in servicios:
        if servicios[sid]["ruta"] in tarifas:
            validos[sid] = servicios[sid]
        else:
            avisos.append("Servicio " + sid + ": su ruta no existe o está incompleta; se ignora.")
    if len(validos) == 0:
        raise ValueError("No hay servicios válidos para operar.")
    asegurar_archivo(base + "transacciones.csv", ENC_TRANSACCIONES)
    asegurar_archivo(base + "indice_reservas.csv", ENC_INDICE)
    asegurar_archivo(base + "movimientos.csv", ENC_MOVIMIENTOS)
    return {"base": base, "servicios": validos, "paradas": paradas, "tarifas": tarifas}, avisos


def ruta_reservas(base, sid, fecha):
    """Devuelve la ruta del archivo de reservas de un servicio y fecha."""
    return base + "reservas/" + sid + "_" + fecha + ".csv"


def cargar_reservas(base, sid, fecha, crear):
    """Lee las reservas de un servicio y fecha como lista de diccionarios.

    Si el archivo no existe y crear es True, lo crea solo con encabezado.
    """
    ruta = ruta_reservas(base, sid, fecha)
    try:
        filas, avisos = leer_csv(ruta, ENC_RESERVAS)
    except FileNotFoundError:
        if crear:
            escribir_csv(ruta, ENC_RESERVAS, [])
        return []
    reservas = []
    vistos = []
    for rid, pas, silla, origen, destino, precio, estado, tx in filas:
        if not precio.isdigit() or estado not in ESTADOS or rid in vistos:
            avisos.append(ruta + ": reserva " + rid + " inválida o repetida; se ignora.")
            continue
        vistos.append(rid)
        reservas.append({"reserva_id": rid, "pasajero_id": pas, "silla": silla,
                         "origen": origen, "destino": destino, "precio": int(precio),
                         "estado": estado, "transaccion_id": tx})
    informar_avisos(avisos)
    return reservas


def guardar_reservas(base, sid, fecha, reservas):
    """Reescribe el archivo de reservas de un servicio y fecha."""
    filas = []
    for r in reservas:
        filas.append([r["reserva_id"], r["pasajero_id"], r["silla"], r["origen"],
                      r["destino"], str(r["precio"]), r["estado"], r["transaccion_id"]])
    escribir_csv(ruta_reservas(base, sid, fecha), ENC_RESERVAS, filas)



def cargar_transacciones(base):
    """Lee transacciones.csv como lista de diccionarios."""
    ruta = base + "transacciones.csv"
    filas, avisos = leer_csv(ruta, ENC_TRANSACCIONES)
    transacciones = []
    for tid, fecha, ida, regreso, subtotal, descuento, total, estado in filas:
        if not (subtotal.isdigit() and descuento.isdigit() and total.isdigit()) \
                or estado not in ESTADOS or ida == "":
            avisos.append("transacciones.csv: transacción " + tid + " inválida; se ignora.")
            continue
        transacciones.append({"transaccion_id": tid, "fecha": fecha, "ida_reserva": ida,
                              "regreso_reserva": regreso, "subtotal": int(subtotal),
                              "descuento": int(descuento), "total": int(total), "estado": estado})
    informar_avisos(avisos)
    return transacciones


def guardar_transacciones(base, transacciones):
    """Reescribe transacciones.csv completo."""
    filas = []
    for t in transacciones:
        filas.append([t["transaccion_id"], t["fecha"], t["ida_reserva"], t["regreso_reserva"],
                      str(t["subtotal"]), str(t["descuento"]), str(t["total"]), t["estado"]])
    escribir_csv(base + "transacciones.csv", ENC_TRANSACCIONES, filas)


def cargar_indice(base):
    """Lee indice_reservas.csv. Devuelve {reserva_id: (servicio_id, fecha)}."""
    filas, avisos = leer_csv(base + "indice_reservas.csv", ENC_INDICE)
    informar_avisos(avisos)
    indice = {}
    for rid, sid, fecha in filas:
        indice[rid] = (sid, fecha)
    return indice


def registrar_movimiento(base, tipo, transaccion_id, detalle):
    """Agrega una línea al historial movimientos.csv (nunca se borra)."""
    ruta = base + "movimientos.csv"
    filas, _ = leer_csv(ruta, ENC_MOVIMIENTOS)
    numero = len(filas) + 1
    agregar_filas(ruta, [[str(numero), tipo, transaccion_id, detalle.replace(",", ";")]])


def ubicar_reserva(ctx, indice, reserva_id, fecha_transaccion):
    """Devuelve (servicio_id, fecha) del archivo que contiene la reserva, o None.

    Primero consulta el índice; si no está, busca en los servicios de la fecha
    de la transacción (útil con datos semilla sin índice).
    """
    if reserva_id in indice:
        return indice[reserva_id]
    for sid in ctx["servicios"]:
        if existe_archivo(ruta_reservas(ctx["base"], sid, fecha_transaccion)):
            for r in cargar_reservas(ctx["base"], sid, fecha_transaccion, False):
                if r["reserva_id"] == reserva_id:
                    return (sid, fecha_transaccion)
    return None
