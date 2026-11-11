

def dias_del_mes(anio, mes):
    """Devuelve la cantidad de días del mes (febrero siempre tienec  28)."""
    dias = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return dias[mes - 1]


def validar_fecha(texto):
    """Valida una fecha AAAA-MM-DD (meses y días)."""
    texto = texto.strip()
    partes = texto.split("-")
    if len(partes) != 3:
        return None, "Formato de fecha inválido."
    anio, mes, dia = partes
    if not (len(anio) == 4 and len(mes) == 2 and len(dia) == 2
            and anio.isdigit() and mes.isdigit() and dia.isdigit()):
        return None, "Formato de fecha inválido. c"
    anio, mes, dia = int(anio), int(mes), int(dia)
    if anio < 2000 or anio > 2100:
        return None, "El año debe estar entre 2000 y 2100."
    if mes < 1 or mes > 12:
        return None, "El mes debe estar entre 01 y 12."
    if dia < 1 or dia > dias_del_mes(anio, mes):
        return None, "Ese día no existe en el mes indicado."
    return texto, ""


def siguiente_fecha(fecha):
    """Devuelve la fecha del día siguiente."""
    anio = int(fecha[0:4])
    mes = int(fecha[5:7])
    dia = int(fecha[8:10]) + 1
    if dia > dias_del_mes(anio, mes):
        dia = 1
        mes += 1
    if mes > 12:
        mes = 1
        anio += 1
    mes_txt = str(mes)
    if mes < 10:
        mes_txt = "0" + mes_txt
    dia_txt = str(dia)
    if dia < 10:
        dia_txt = "0" + dia_txt
    return str(anio) + "-" + mes_txt + "-" + dia_txt


def fechas_en_rango(fecha_inicial, fecha_final, limite=366):
    """Lista las fechas entre dos fechas válidas."""
    fechas = []
    actual = fecha_inicial
    while actual <= fecha_final and len(fechas) < limite:
        fechas.append(actual)
        actual = siguiente_fecha(actual)
    return fechas


def validar_hora(texto):
    """Valida una hora HH:MM de 24 horas."""
    texto = texto.strip()
    partes = texto.split(":")
    if len(partes) != 2 or len(partes[0]) != 2 or len(partes[1]) != 2:
        return None, "Hora inválida. Use HH:MM."
    if not (partes[0].isdigit() and partes[1].isdigit()):
        return None, "Hora inválida. Use HH:MM."
    if int(partes[0]) > 23 or int(partes[1]) > 59:
        return None, "Hora fuera de rango."
    return texto, ""


def validar_pasajero(texto):
    """Valida el identificador del pasajero ."""
    valor = texto.strip().upper()
    if valor == "" or len(valor) > 20:
        return None, "El pasajero debe tener entre 1 y 20 caracteres."
    if not valor.replace("-", "").replace("_", "").isalnum():
        return None, "Use solo letras, números, guion o guion bajo."
    return valor, ""


def parsear_silla(texto, filas, columnas):
    """Convierte «2A» o «F2 S A» a índices (fila, columna) de la matriz.

    Devuelve ((fila_idx, col_idx), "") o (None, mensaje_error).
    """
    t = texto.strip().upper()
    fila_txt = ""
    letra = ""
    if " " in t:
        partes = t.split()
        if (len(partes) == 3 and partes[0][0] == "F" and partes[0][1:].isdigit()
                and partes[1] == "S" and len(partes[2]) == 1):
            fila_txt = partes[0][1:]
            letra = partes[2]
    elif len(t) >= 2 and t[:-1].isdigit():
        fila_txt = t[:-1]
        letra = t[-1]
    if fila_txt == "" or not letra.isalpha():
        return None, "Formato de silla inválido. Use «2A» o «F2 S A»."
    fila = int(fila_txt)
    columna = ord(letra) - ord("A")
    if fila < 1 or fila > filas:
        return None, "La fila debe estar entre 1 y " + str(filas) + "."
    if columna < 0 or columna >= columnas:
        return None, "La columna debe estar entre A y " + chr(64 + columnas) + "."
    return (fila - 1, columna), ""


def pedir(mensaje, validar, extra=None):
    """Pide un dato hasta que sea válido. Devuelve None si el usuario escribe 0."""
    while True:
        texto = input(mensaje + " (0 = cancelar): ").strip()
        if texto == "0":
            return None
        valor, error = validar(texto, extra)
        if valor is not None:
            return valor
        print(error)


def pedir_confirmacion(mensaje):
    """Pregunta S/N hasta recibir una respuesta válida. Devuelve True/False."""
    while True:
        respuesta = input(mensaje + " (S/N): ").strip().upper()
        if respuesta == "S":
            return True
        if respuesta == "N":
            return False
        print(" Responda S o N.")
