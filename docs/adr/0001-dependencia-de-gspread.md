# ADR 0001 — Dependencia de gspread: mantener, adaptar o reemplazar

- **Estado:** Aceptado — opción B implementada; opción C **activada** (disparador cumplido,
  ver actualización 2026-06-10)
- **Fecha:** 2026-06-08 (actualizado 2026-06-10)

> **Actualización 2026-06-10 — disparador cumplido:** los maintainers de gspread anunciaron
> que no pueden seguir manteniendo la librería y buscan nuevos maintainers (ver README del
> repositorio de gspread). Conforme a la política de este ADR, se ejecuta la opción C: el
> cliente nativo (spike en `infrastructure/native/`) se promueve a adaptador de primera
> clase de forma incremental — primero opt-in (`backend="native"`), gspread como default
> hasta la 3.0, donde el nativo pasa a ser el default y gspread queda como extra opcional.
> Ver el plan de 10 sprints en el ROADMAP.
- **Contexto del proyecto:** GSpreadManager 2.0 (refactor a Clean Architecture / DDD táctico)

## Contexto

GSpreadManager se apoya en [`gspread`](https://github.com/burnash/gspread) como cliente de
Google Sheets / Drive. Durante la revisión arquitectónica surgió la duda de si conviene
seguir dependiendo de gspread o construir un cliente propio, motivada por:

1. **Señales de mantenimiento de gspread.** Último release **6.2.1 (mayo 2025)**, con
   cadencia sana en 2024–2025 pero enfriándose, y señales públicas de **falta de capacidad
   de mantenimiento** / búsqueda de nuevos mantenedores. La API que envuelve
   (Google Sheets API v4 / Drive v3) es **estable**, por lo que "pocos commits" indica tanto
   madurez como riesgo de *bus factor* — no que esté roto.
2. **Fricción de tipado.** Al extraer la capa de aplicación (Sprint 5) se intentó tipar los
   servicios contra Protocols nominales `WorksheetPort` / `SpreadsheetPort`. Las firmas
   concretas de gspread (ej. `batch_update(data: Iterable[MutableMapping],
   value_input_option: ValueInputOption | None, ...)`) **no satisfacen** Protocols limpios sin
   acoplar el puerto a los tipos de gspread o envolver cada objeto en adaptadores. Como
   solución provisional los servicios reciben la hoja/documento *duck-typed* (`Any`).

**Hecho clave:** tras los Sprints 1–5, gspread ya está **aislado en `infrastructure/`**
(`auth.py`, `gspread_client.py`, `request_builders.py`, `pandas_adapter.py` y las llamadas
duck-typed de los servicios). El dominio, los puertos y la capa de aplicación **no lo
importan**. Reemplazar gspread es hoy un cambio **contenido en infraestructura**, no un
re-rewrite.

> Observación que unifica el problema: **la fricción de tipado y la "reemplazabilidad" de
> gspread tienen la misma solución** — definir puertos nominales *propios* + adaptadores. Si
> el puerto lo define GSpreadManager (no las firmas de gspread), el tipado queda limpio y un
> futuro cliente nativo que implemente los mismos puertos es un *drop-in*.

## Decisión a tomar

¿Cómo gestionamos la dependencia de gspread de cara a la 2.0?

## Opciones

### Opción A — Mantener gspread tal cual (duck-typed)

Dejar los servicios con parámetros `Any` y seguir usando gspread directamente desde el
conector/infraestructura.

- **Esfuerzo:** nulo.
- **Riesgo técnico:** bajo a corto plazo; el *bus factor* de gspread queda sin mitigar.
- **Tipado:** el borde con gspread queda sin puerto nominal (parcialmente `Any`).
- **Reemplazabilidad:** baja-media (habría que crear la costura cuando haga falta).

### Opción B — Puertos nominales + adaptadores sobre gspread (recomendada)

Definir `SheetsClientPort` / `WorksheetPort` / `SpreadsheetPort` con **nuestras** firmas, y
adaptadores `GspreadWorksheet` / `GspreadSpreadsheet` (en `infrastructure/`) que los
implementan envolviendo gspread y convirtiendo lo necesario (ej. `value_input_option`).

- **Esfuerzo:** medio-bajo (un sprint; ~2–3 adaptadores + ajustar el cableado y los tipos).
- **Riesgo técnico:** bajo (los tests siguen verdes; gspread sigue siendo el motor real).
- **Tipado:** **se resuelve** — la capa de aplicación pasa a depender de puertos nominales.
- **Reemplazabilidad:** **alta** — gspread queda como un detalle 100% sustituible.
- **Mantenimiento:** seguimos delegando los quirks de la API a gspread.

### Opción C — Cliente propio nativo (REST directo)

Reemplazar gspread por un `SheetsApiClient` propio que llame a la Google Sheets API v4 /
Drive v3 usando la sesión autorizada de `google-auth` (que **ya** usamos y es oficial de
Google), detrás de los mismos puertos de la Opción B.

- **Esfuerzo:** alto. Hay que reimplementar, para nuestro subconjunto (~35 operaciones):
  sesión HTTP autorizada, llamadas a `values.get/update/append/batchUpdate`,
  `spreadsheets.batchUpdate` (formato/validación/condicional), `spreadsheets.create`,
  Drive `files.create/copy/delete/list` y `permissions.*`, **conversiones A1 ↔ GridRange**
  (incluyendo > 26 columnas), parsing de errores, paginación y reintentos.
- **Riesgo técnico:** medio-alto al inicio (heredamos como bugs nuevos el detalle que gspread
  ya resolvió y tiene *battle-tested*). Disminuye con tests y uso.
- **Tipado / control:** máximo — tipos nativos limpios, podemos exponer features que gspread
  no expone, sin terceros en el camino.
- **Mantenimiento:** pasamos a ser **los únicos mantenedores** del cliente HTTP. Mitigado por
  lo estable que es la Sheets API v4 y por usar `google-auth` (oficial) para lo sensible.
- **Valor para el usuario:** nulo de forma directa (es un *swap* like-for-like); el valor es
  estratégico (independencia, control).

## Criterios de comparación

| Criterio | A: gspread tal cual | B: puertos + adaptadores | C: cliente propio |
|---|---|---|---|
| Esfuerzo | Nulo | Medio-bajo | Alto |
| Riesgo a corto plazo | Bajo | Bajo | Medio-alto |
| Resuelve el tipado | No | **Sí** | Sí |
| Reemplazabilidad de gspread | Baja | **Alta** | Total |
| Mantenimiento propio | Bajo | Bajo | **Alto** |
| Control / features | Bajo | Bajo | **Máximo** |
| Mitiga el *bus factor* | No | Parcial (deja la puerta abierta) | **Sí** |

## Decisión

Se adopta **Opción B** (implementada) y se difiere **Opción C** con un **disparador
explícito**: el reemplazo total de gspread por un cliente propio nativo se ejecuta si gspread
es declarado **EOL** o su **repositorio queda inactivo** (sin releases ni actividad de
mantenimiento por un período prolongado). Mientras tanto, los adaptadores de gspread siguen
siendo el motor por defecto, detrás de los puertos ya definidos.

## Recomendación (histórica)

Adoptar **Opción B ahora** y dejar **Opción C como decisión diferida**:

1. **Sprint próximo (B):** introducir los puertos nominales y los adaptadores sobre gspread.
   Resuelve el tipado, crea la costura y convierte a gspread en un detalle sustituible — todo
   con bajo riesgo y sin romper comportamiento.
2. **Más adelante, opcional (C):** construir un `SheetsApiClient` nativo **detrás de los
   mismos puertos** como *spike*, ejecutarlo en paralelo a gspread (A/B) y promoverlo a
   default solo si demuestra robustez, dejando el adaptador de gspread como *fallback*.

Racional: no bloquear la 2.0 en un *rewrite* grande sin valor de usuario directo, pero
garantizar la **opción de salida** si el mantenimiento de gspread se deteriora. No
necesitamos "superar a gspread" para la comunidad: solo **dueñar un cliente fino** para las
operaciones que exponemos, y eso es mucho más acotado.

## Consecuencias

- **Si B:** la capa de aplicación queda 100% tipada contra puertos propios; el reemplazo
  futuro de gspread no toca dominio ni aplicación. Coste: una capa fina de adaptadores a
  mantener.
- **Si más tarde C:** independencia total del tercero y control de features, a cambio de
  asumir el mantenimiento del cliente HTTP y el *battle-testing* inicial.
- **Si A (no hacer nada):** se mantiene el `Any` en el borde y el *bus factor* sin mitigar;
  reabrir la costura costará más cuando urja.

## Hallazgos del spike del cliente nativo (opción C)

Se implementó un spike **no cableado** (`gspreadmanager.infrastructure.native`, ~400 LOC) que
implementa los mismos puertos llamando a la Sheets API v4 / Drive API v3 vía una sesión
autorizada de google-auth. Conclusiones:

- **Factibilidad: confirmada.** Las partes "difíciles" quedan resueltas y son baratas: la
  autenticación reusa `google.auth.transport.requests.AuthorizedSession` (no agrega
  dependencias más allá de google-auth) y las utilidades A1 propias (`rowcol_to_a1`,
  `column_to_letter`, `a1_to_grid_range`) son ~50 LOC, con **paridad verificada por test**
  contra `gspread.utils.a1_range_to_grid_range`.
- **Cubierto y testeado (sesión HTTP falsa):** apertura por nombre (Drive search + metadata),
  lectura con *padding* rectangular, escrituras (`values.update`/`append`/`values:batchUpdate`),
  **formato/freeze/merge** (`repeatCell`/`updateSheetProperties`/`mergeCells`) y
  **validación/condicional** (`spreadsheets:batchUpdate`; los *request builders* ya producen
  los dicts crudos), gestión de hojas (`addSheet`/`deleteSheet`), **permisos de Drive**
  (`share`/`list`/`remove`), `find`/`range`/`col`/`row` y **paginación** del listado.
- **Mapeo de errores:** un único punto (`_ensure_ok`, al estilo de `gspread.HTTPClient.request`)
  convierte los status HTTP no exitosos en `SheetsApiError` (parsea `{"error": {...}}` con
  fallback al texto), integrado a la jerarquía `GSpreadManagerError`.
- **Test de contrato:** `tests/test_port_contract.py` verifica que **ambos** adaptadores
  (gspread y nativo) exponen la superficie completa de cada puerto ⇒ son intercambiables.
- **Pendientes menores:** mover a carpeta en `create` (Drive PATCH), semántica de `with_link` y
  el padding exacto al rango usado de la hoja (el spike rellena al ancho máximo de los datos).
- **Esfuerzo para completar C:** lo grueso ya está; resta **~0,5 sprint** de pulido (carpeta en
  create, edge cases) + *battle-testing* contra la API real. El `RetryPolicy` ya existe y solo
  habría que envolver las llamadas HTTP.
- **Riesgo principal:** heredar detalles sutiles que gspread ya resolvió (padding exacto,
  *quoting* de títulos con comillas, formatos de error, cuotas). Mitigable con tests de contrato.

Conclusión: la opción C es **viable y mayormente construida** en el spike; se mantiene
**diferida** hasta el disparador (EOL/inactividad de gspread), con el spike como base lista.

## Referencias

- gspread — repositorio: <https://github.com/burnash/gspread>
- gspread — PyPI (6.2.1, 2025-05): <https://pypi.org/project/gspread/>
- Google Sheets API v4: <https://developers.google.com/sheets/api>
- Google Drive API v3: <https://developers.google.com/drive/api>
- Análisis competitivo del proyecto: [competitive-analysis.md](../competitive-analysis.md)
