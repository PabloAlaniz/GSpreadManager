# Análisis competitivo

Comparación de **GSpreadManager** con las principales librerías del ecosistema Python para
Google Sheets, y derivación del roadmap (ver
[ROADMAP.md](https://github.com/PabloAlaniz/GSpreadManager/blob/main/ROADMAP.md)).

_Última actualización: junio 2026._

## Posicionamiento

GSpreadManager compite en la capa de **wrapper amigable sobre la Google Sheets API**.
Sus rivales directos son `gspread` (la base que ya usa) y su ecosistema de extensiones,
más `pygsheets` y `EZSheets`.

| Capacidad | **GSpreadManager** | gspread | pygsheets | gspread-pandas | EZSheets |
|---|:--:|:--:|:--:|:--:|:--:|
| Leer/escribir celdas, filas, rangos | ✅ | ✅ | ✅ | ✅ | ✅ |
| Salida list / dict / pandas | ✅ | parcial | ✅ | ✅ (DF) | parcial |
| Crear/eliminar pestañas | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch update | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Retry + backoff ante cuota | ✅ | ⚠️ manual | ✅ | hereda | ⚠️ |
| Type hints + `py.typed` | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Caché de cliente/documento | ✅ (v1.1) | ✅ | ✅ | ✅ | ✅ |
| Autenticación flexible (SA, OAuth, ADC) | ✅ (v1.1) | ✅ | ✅ | ✅ | ✅ (OAuth) |
| **Formato de celdas** | ❌ | vía `gspread-formatting` | ✅ nativo | parcial | ❌ |
| **Crear/copiar/borrar documento** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Compartir / permisos** | ❌ | ✅ | ✅ | ⚠️ | ⚠️ |
| **Listar archivos (Drive)** | ❌ | ⚠️ | ✅ | ❌ | ✅ |
| **Async** | ❌ | vía `gspread-asyncio` | ❌ | ❌ | ❌ |
| Data validation (dropdowns/checkbox) | ❌ | ⚠️ | ✅ | ❌ | ❌ |
| Freeze / merge / filtros | ❌ | ⚠️ | ✅ | ✅ | parcial |
| Named / protected ranges | ❌ | ⚠️ | ✅ | ❌ | ❌ |
| Caché de lecturas | ❌ | ❌ | ⚠️ | ❌ | ❌ |
| Docs en español | ✅ único | ❌ | ❌ | ❌ | ❌ |

Leyenda: ✅ soportado · ⚠️ parcial/indirecto · ❌ no soportado.

## Conclusiones

**Diferenciales de GSpreadManager**

- Simplicidad y API pythónica con **documentación en español** (único en el segmento).
- Tipado completo (PEP 561), reintentos con backoff y excepciones propias **de fábrica**.
- A partir de v1.1: caché de cliente/documento y autenticación flexible, cerrando la brecha
  de eficiencia y auth frente a la competencia.

**Brechas principales a cerrar (origen del roadmap)**

1. **Formato de celdas** (color, negrita, formato numérico, condicional) — lo tienen
   `pygsheets` y `gspread-formatting`.
2. **Operaciones a nivel documento/Drive**: crear, copiar, borrar y listar spreadsheets.
3. **Compartir / gestión de permisos**.
4. **Async** para aplicaciones modernas (referencia: `gspread-asyncio`).
5. **Productividad de datos**: pandas avanzado (anclaje, `drop_empty`), freeze/merge/filtros,
   data validation.

## Fuentes

- [gspread](https://docs.gspread.org/en/latest/) y [extensiones de la comunidad](https://docs.gspread.org/en/latest/community.html)
- [pygsheets](https://github.com/nithinmurali/pygsheets)
- [gspread-pandas](https://github.com/aiguofer/gspread-pandas)
- [gspread-dataframe](https://github.com/robin900/gspread-dataframe)
- [gspread-formatting](https://pypi.org/project/gspread-formatting/)
- [gspread-asyncio](https://gspread-asyncio.readthedocs.io/)
- [EZSheets](https://pypi.org/project/EZSheets/)
