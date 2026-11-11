"""Cálculos y reglas de negocio puras (sin entrada/salida por consola ni archivos)."""


def posiciones(paradas_ruta):
    """Devuelve {codigo_parada: posicion} para una ruta."""
    pos = {}
    for k in range(len(paradas_ruta)):
        pos[paradas_ruta[k]] = k
    return pos


def validar_trayecto(paradas_ruta, origen, destino):
    """Valida origen/destino en la ruta y que origen preceda al destino.

    Devuelve (i, j, "") o (None, None, mensaje_error).
    """
    pos = posiciones(paradas_ruta)
    if origen not in pos:
        return None, None, "El origen " + origen + " no pertenece a la ruta (" + "-".join(paradas_ruta) + ")."
    if destino not in pos:
        return None, None, "El destino " + destino + " no pertenece a la ruta (" + "-".join(paradas_ruta) + ")."
    if pos[origen] >= pos[destino]:
        return None, None, "El origen debe aparecer antes que el destino en la ruta."
    return pos[origen], pos[destino], ""


def tarifa_trayecto(tarifas_ruta, i, j):
    """Suma las tarifas regulares de los tramos consecutivos entre i y j."""
    total = 0
    for k in range(i, j):
        total += tarifas_ruta[k]
    return total


def clase_de_fila(fila_idx, filas_premium):
    """Devuelve 'PREMIUM' para las primeras filas_premium filas; si no, 'REGULAR'."""
    if fila_idx < filas_premium:
        return "PREMIUM"
    return "REGULAR"


def precio_silla(tarifa_regular, clase):
    """Precio de la silla: PREMIUM = 1,5 * tarifa regular (aritmética entera)."""
    if clase == "PREMIUM":
        return tarifa_regular * 3 // 2
    return tarifa_regular


def calcular_totales(precios):
    """Devuelve (subtotal, descuento, total). Con ida y regreso hay 10 % de descuento."""
    subtotal = sum(precios)
    descuento = 0
    if len(precios) == 2:
        descuento = subtotal * 10 // 100
    return subtotal, descuento, subtotal - descuento


def se_solapan(inicio1, fin1, inicio2, fin2):
    """Intervalos [inicio, fin): hay conflicto si max(inicios) < min(fines)."""
    return max(inicio1, inicio2) < min(fin1, fin2)


def codigo_silla(fila_idx, col_idx):
    """Convierte índices de matriz a código de silla, p. ej. (1, 0) -> '2A'."""
    return str(fila_idx + 1) + chr(ord("A") + col_idx)


def buscar_conflicto(reservas, pos, codigo, i, j):
    """Devuelve la reserva ACTIVA que bloquea la silla para [i, j), o None."""
    for r in reservas:
        if r["estado"] != "ACTIVA" or r["silla"] != codigo:
            continue
        if r["origen"] not in pos or r["destino"] not in pos:
            return r  # dato corrupto: se bloquea por seguridad
        if se_solapan(i, j, pos[r["origen"]], pos[r["destino"]]):
            return r
    return None


def construir_matriz(servicio, reservas, pos, i, j):
    """Matriz de filas * columnas con 'O' (libre) o 'X' (no disponible) para [i, j)."""
    matriz = []
    for f in range(servicio["filas"]):
        fila = []
        for c in range(servicio["columnas"]):
            if buscar_conflicto(reservas, pos, codigo_silla(f, c), i, j) is None:
                fila.append("O")
            else:
                fila.append("X")
        matriz.append(fila)
    return matriz


def contar_libres(matriz):
    """Cuenta las sillas libres ('O') de una matriz."""
    libres = 0
    for fila in matriz:
        for celda in fila:
            if celda == "O":
                libres += 1
    return libres


def ocupacion_por_tramo(reservas, pos, n_paradas):
    """Sillas ocupadas (reservas ACTIVAS) en cada tramo contiguo de la ruta."""
    ocupadas = [0] * (n_paradas - 1)
    for r in reservas:
        if r["estado"] == "ACTIVA" and r["origen"] in pos and r["destino"] in pos:
            for k in range(pos[r["origen"]], pos[r["destino"]]):
                ocupadas[k] += 1
    return ocupadas


def pico_ocupacion(ocupadas):
    """Devuelve (maximo, indice_del_tramo) de una lista de ocupaciones."""
    mayor = 0
    indice = 0
    for k in range(len(ocupadas)):
        if ocupadas[k] > mayor:
            mayor = ocupadas[k]
            indice = k
    return mayor, indice


def formato_dinero(valor):
    """Formatea un entero como $50.000."""
    return "$" + format(valor, ",").replace(",", ".")
