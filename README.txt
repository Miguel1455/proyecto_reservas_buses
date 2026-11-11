# Reservas de buses por tramos (Proyecto final Python · Tema 5)

Aplicación 100 % de consola. Solo usa lo visto en el curso: archivos, ciclos, ciclos anidados,
conceptos básicos, control de errores (`try/except`), diccionarios, listas/matrices, funciones y strings.
**No importa ninguna librería externa** (ni numpy, csv, os, sys o datetime); los CSV se leen con `split(",")`.

## Ejecutar
Desde la carpeta del proyecto (donde están los `.py` y la carpeta `datos/`):
```
python main.py
python pruebas.py
```
- `main.py` abre el menú y usa la carpeta `datos/`. Para usar otra, cambie `CARPETA_DATOS` en `main.py`.
- `pruebas.py` ejecuta 12 comprobaciones automáticas sobre `datos_prueba/` (la deja en estado semilla al empezar).
- Las carpetas `datos/` y `datos/reservas/` deben existir (vienen incluidas; sin `os` el programa no puede crearlas).

## Archivos
| Archivo / carpeta | Rol |
|---|---|
| `main.py` | Punto de entrada. Carga los datos y lanza el menú. |
| `consola.py` | Menú y flujos de interacción. |
| `operaciones.py` | Reservar, ida y regreso atómico, cancelar, tiquetes. |
| `logica.py` | Reglas puras: solapamiento, precios, matriz de sillas, ocupación. |
| `reportes.py` | Manifiesto, ocupación por tramo, ingresos, top 3 y exportación. |
| `archivos.py` | Lectura, validación y escritura de CSV. |
| `validaciones.py` | Fechas, horas, sillas, pasajeros y lectura de datos con `pedir()`. |
| `pruebas.py` | Pruebas automáticas. |
| `datos/` | Datos semilla: `servicios.csv`, `paradas.csv`, `tramos.csv`, `transacciones.csv` y `reservas/`. |
| `datos_prueba/` | Copia de los datos semilla que usa `pruebas.py`. |
| `ejemplos_salida/` | Ejemplos de sesiones y de archivos generados por el programa. |

Archivos que el programa crea o actualiza:
- `reservas/<servicio>_<fecha>.csv`: uno por servicio y fecha; nace solo con el encabezado al consultarlo por primera vez.
- `transacciones.csv`: una fila por compra, con el vínculo entre ida y regreso.
- `indice_reservas.csv`: en qué servicio y fecha está cada reserva (sirve para ubicar la ida y el regreso al cancelar).
- `movimientos.csv`: historial de operaciones; solo se agrega, nunca se borra.
- `reporte_ruta.txt` y `ocupacion_tramos.csv`: cada reporte se agrega como una nueva «corrida»; no se sobrescriben los anteriores.

## Formatos de silla aceptados
- `2A` (fila + letra).
- `F2 S A` (fila 2, silla A).
- Fila 1 = PREMIUM (1,5 × tarifa regular). Filas 2 a 4 = REGULAR.

## Reglas clave
- Cada viaje es un intervalo `[i, j)` de posiciones de parada. Dos reservas de la misma silla chocan si `max(inicio1, inicio2) < min(fin1, fin2)`; coincidir solo en la parada de bajada/subida no es conflicto.
- El precio es la suma de las tarifas de los tramos entre origen y destino.
- Ida y regreso: el regreso debe ir de destino a origen de la ida, en fecha igual o posterior. Se validan ambos viajes y solo entonces se escribe; si algo falla, no se guarda nada. Descuento del 10 % sobre la suma.
- Cancelar: las reservas y la transacción pasan a `CANCELADA` (no se borran) y solo se cancela una transacción `ACTIVA`.
- Ingresos: suma el `total` de las transacciones `ACTIVA`, una vez por transacción, asignado a la ruta y fecha del viaje de ida.
- En cualquier pregunta, escribir `0` cancela y vuelve al menú. Ante datos inválidos el programa informa y vuelve a preguntar.
- Las filas mal formadas de los CSV se ignoran con un aviso; si falta un archivo obligatorio, el programa lo informa y termina sin error.

## Pruebas manuales (ejecutar `python main.py`)
Partiendo de los datos semilla de `datos/`:

| # | Pasos (menú) | Resultado esperado |
|---|---|---|
| 1 Reutilización legal | Opción 3: B001, 2026-11-12, RIO→BOG, silla `2A`, pasajero C02 | Se confirma (la semilla ya tiene MED→RIO en 2A). |
| 2 Solapamiento | Opción 3: B001, 2026-11-12, MED→MAR, silla `2A` | Se rechaza porque se solapa con una reserva; los archivos no cambian. |
| 3 Precio | Opción 1: origen MED, destino MAR, fecha 2026-11-12 | REGULAR $50.000 y PREMIUM $75.000. |
| 4 Ida y regreso | Opción 4: ida B001 MED→MAR 2026-11-12 silla `2B`; regreso B002 2026-11-13 silla `2B` | Subtotal $100.000, descuento $10.000, total $90.000. |
| 5 Atomicidad | Opción 3: B002 2026-11-14 MAR→MED silla `2B`. Luego opción 4 con ida B001 MED→MAR 2026-11-14 silla `2B` y regreso B002 2026-11-14 silla `2B` | El regreso `2B` se rechaza; al escribir `0` no se crea ida ni tiquete. |
| 6 Fechas | Reservar `3C` MED→BOG el 2026-11-12; ver el mapa (opción 2) del 2026-11-13 | `3C` está libre el 13 (archivos distintos). |
| 7 Reinicio | Salir con `0`, volver a ejecutar, opción 5 → 1 con una transacción creada | Se recuperan reservas y tiquetes sin duplicados. |
| 8 Cancelación | Opción 5 → 3 sobre una transacción activa; repetirlo | Pasa a CANCELADA y la silla queda libre; la segunda vez se rechaza. |
| 9 Errores | Fecha `2026-02-30`, silla `9Z`, opción `99`, destino anterior al origen | Mensaje de error y el programa continúa. |

`python pruebas.py` automatiza estos casos (resultado de ejemplo en `ejemplos_salida/resultado_pruebas.txt`).