# Benchmarks: gspread vs cliente nativo

Desde la v2.2, GSpreadManager tiene dos transportes intercambiables detrás de los mismos
puertos: el adaptador de **gspread** y el **cliente nativo** (REST directo sobre
`google-auth`). Ambos exponen exactamente la misma API; este benchmark compara su
rendimiento contra la API real.

## Cómo correrlo

Requiere un service account con la Sheets API y la Drive API habilitadas:

```bash
export GSPREADMANAGER_TEST_CREDENTIALS=/ruta/al/service-account.json
python benchmarks/run_benchmarks.py --rounds 5
```

El script crea un documento temporal, ejecuta cada operación N veces por backend
(descartando la primera ejecución, que paga la autenticación), reporta la **mediana** y
borra el documento al terminar. La salida es una tabla Markdown como la de abajo.

## Operaciones medidas

| Operación | Qué ejercita |
|---|---|
| read completo (201 filas) | `values.get` + padding rectangular |
| read rango (A1:C50) | `values.get` por rango |
| append 1 fila | `values.append` |
| batch_update (50 filas) | `values:batchUpdate` |
| update_cell | `values.update` de una celda |
| formato encabezado | `spreadsheets:batchUpdate` (repeatCell) |

## Resultados

> Pendiente de publicar: correr el script con credenciales reales y pegar la tabla aquí.
> Los tiempos dependen de la red y la región; lo relevante es la tendencia relativa.

Lo esperable: tiempos dominados por la latencia de la API de Google (decenas a cientos de
ms por petición), con diferencias chicas entre backends. El nativo ahorra una capa de
indirección y aplica **timeout por petición** (`http_timeout`, default 60s), algo que
gspread no ofrece.

## Consideraciones

- La cuota por defecto de la API es de 60 lecturas y 60 escrituras por minuto por usuario:
  subí `--rounds` con cuidado o activá `rate_limit=` en producción.
- El warm-up descartado incluye autenticación y resolución del documento (con caché en
  ambos backends, las rondas siguientes no la repiten).
- Para repetir en CI haría falta un secreto con credenciales; hoy el benchmark es manual,
  como la suite de integración (`pytest -m integration`).
