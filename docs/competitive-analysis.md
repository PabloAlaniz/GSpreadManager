# Análisis competitivo

Comparación de **GSpreadManager** con las librerías del ecosistema Python para Google Sheets,
y derivación del [ROADMAP](https://github.com/PabloAlaniz/GSpreadManager/blob/main/ROADMAP.md).

_Última actualización: junio 2026 (post 2.0)._

## Posicionamiento

GSpreadManager es un **wrapper amigable y tipado** sobre la Google Sheets API con arquitectura
por capas (dominio / aplicación / infraestructura / puertos) y gspread aislado y reemplazable
(ver [ADR 0001](adr/0001-dependencia-de-gspread.md)). Compite con `gspread` y su ecosistema de
extensiones, `pygsheets`, `sheetfu` y `EZSheets`. La referencia de bajo nivel es el cliente
oficial `google-api-python-client`.

## Competidores

| Librería | Enfoque | Estado |
|---|---|---|
| **gspread** | El wrapper de facto sobre Sheets API. | Maduro; mantenimiento desacelerado (último release may-2025) |
| **pygsheets** | Wrapper rico (formato, named ranges, pandas). | Maduro; baja actividad |
| **gspread-pandas** | DataFrames sobre gspread. | Activo (capa fina) |
| **gspread-dataframe** | `get_as_dataframe` / `set_with_dataframe`. | Mantenido |
| **gspread-formatting** | Formato + validación + condicional sobre gspread. | Mantenido |
| **gspread-asyncio** | Wrapper async (threadpool) sobre gspread. | Mantenido |
| **sheetfu** | Estilo ORM, orientado a batch. | Baja actividad |
| **EZSheets** | Mínimo y didáctico (Al Sweigart). | Mantenido |
| **df2gspread** | Subida de DataFrames (legado). | Obsoleto |
| **google-api-python-client** | Cliente oficial de bajo nivel (todo, verboso). | Oficial, activo |

## Tabla comparativa

| Capacidad | **GSpreadManager 2.0** | gspread (+ext) | pygsheets | gspread-pandas | sheetfu | EZSheets |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Leer/escribir celdas, filas, rangos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Salida list / dict / pandas | ✅ | parcial | ✅ | ✅ (DF) | ⚠️ | parcial |
| Crear/eliminar/limpiar pestañas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch update | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Retry + backoff ante cuota | ✅ | ⚠️ manual | ✅ | hereda | ⚠️ | ⚠️ |
| Type hints + `py.typed` | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Caché de cliente/documento | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Auth flexible (SA file/dict, OAuth, ADC, cliente) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ (OAuth) |
| **Formato de celdas** (color/fuente/número) | ✅ nativo | vía `gspread-formatting` | ✅ | parcial | ⚠️ | ❌ |
| **Formato condicional** | ✅ | vía ext | ✅ | ❌ | ❌ | ❌ |
| **Data validation** (dropdown/checkbox) | ✅ | vía ext | ✅ | ❌ | ❌ | ❌ |
| **Freeze / merge** | ✅ | ⚠️/ext | ✅ | parcial | ⚠️ | parcial |
| **Crear/copiar/borrar documento (Drive)** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| **Compartir / permisos** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| **Listar archivos (Drive)** | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Handles inmutables sin "hoja activa" global | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Backend reemplazable (puertos / hexagonal) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Docs en español | ✅ único | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Notas de celda** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Named ranges** | ❌ | ✅ | ✅ | ❌ | ⚠️ | ❌ |
| **Protected ranges** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Sort / basic filter** | ❌ | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| **Insert/delete/resize/hide filas y columnas** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| **Type inference de valores** (`numericise`) | ✅ | ✅ | ✅ | ✅ (DF) | ⚠️ | ⚠️ |
| **Abrir por key / URL** | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| **Export (xlsx/csv/pdf) / import CSV** | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Async** | ❌ | vía `gspread-asyncio` | ❌ | ❌ | ❌ | ❌ |
| Caché de lecturas con invalidación | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |

Leyenda: ✅ soportado · ⚠️ parcial/indirecto · ❌ no soportado.

## Features de gspread que (todavía) no tenemos

Candidatas a sumar, ordenadas por valor percibido. (✅ ya hechas: abrir por key/URL, type inference, filas/columnas estructurales).

1. **Notas de celda** (get/insert/update/clear note).
2. **Named ranges** (definir/listar/eliminar) y **protected ranges**.
3. **Sort y basic filter** (ordenar un rango; filtro básico).
4. **Export / import**: exportar a xlsx/csv/pdf; `import_csv`.
5. **Unmerge** (tenemos `merge`, falta `unmerge_cells`).
6. **Tab color**, **update_title/locale/timezone**, **listar worksheets** y abrir por índice/id.

## Oportunidades (lo que casi nadie tiene y podríamos diferenciar)

Más allá de la paridad, dónde podemos liderar:

- **Async de verdad** (no threadpool): cliente `asyncio`-native sobre `httpx`, detrás de los
  mismos puertos. gspread depende de `gspread-asyncio` (threadpool).
- **Backend reemplazable / testeable sin red**: gracias a los puertos, exponer un *fake*
  in-memory para tests de usuarios y, a futuro, el cliente nativo REST (ver ADR 0001).
- **Mapeo de filas a modelos tipados** (dataclasses/Pydantic): leer/escribir filas como objetos
  con esquema y validación — muy "tech actual", nadie lo ofrece de fábrica.
- **Caché de lecturas con invalidación al escribir** (opcional): clave para apps que releen.
- **Backend de DataFrame pluggable**: además de pandas, soportar **polars** vía el
  `DataFramePort` (ya existe el puerto).
- **Rate limiting proactivo** (token bucket) además del retry reactivo, para no chocar la cuota.
- **Operaciones de alto nivel**: `upsert` por clave, *find-or-create* de pestaña, *bulk* con
  control de batch automático, *paginación/streaming* para hojas grandes.
- **CLI** (`gspreadmanager read/append/export ...`).
- **Documentación bilingüe (es/en)**: ya somos únicos en español; sumar inglés amplía alcance.

## Conclusiones

- **Brecha cerrada:** con la 2.0, formato, validación, condicional, Drive y permisos ya están a
  la par de pygsheets/gspread+ext (eran las grandes ausencias de la 1.x).
- **Próxima paridad (v2.1):** abrir por key/URL, type inference, manipulación de filas/columnas,
  notas y named/protected ranges — lo que aún nos separa de gspread/pygsheets.
- **Diferenciación:** arquitectura hexagonal (backend reemplazable, testeable sin red), tipado
  estricto, retry de fábrica, modelos de fila tipados y async nativo — terreno donde el
  ecosistema actual es débil.

## Fuentes

- [gspread](https://docs.gspread.org/) y [extensiones de la comunidad](https://docs.gspread.org/en/latest/community.html)
- [pygsheets](https://github.com/nithinmurali/pygsheets) ·
  [gspread-pandas](https://github.com/aiguofer/gspread-pandas) ·
  [gspread-dataframe](https://github.com/robin900/gspread-dataframe)
- [gspread-formatting](https://pypi.org/project/gspread-formatting/) ·
  [gspread-asyncio](https://gspread-asyncio.readthedocs.io/)
- [sheetfu](https://github.com/socialpoint-labs/sheetfu) ·
  [EZSheets](https://pypi.org/project/EZSheets/) ·
  [df2gspread](https://pypi.org/project/df2gspread/)
- [google-api-python-client](https://github.com/googleapis/google-api-python-client) (oficial)
