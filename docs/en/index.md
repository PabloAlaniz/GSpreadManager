# GSpreadManager (English overview)

GSpreadManager is a typed, friendly Python wrapper for Google Sheets with a hexagonal
architecture: a **native REST client** (default since 3.0) and a gspread adapter behind
the same ports, fully swappable and testable without network access.

> Full documentation is currently in Spanish (the rest of this site). This page covers
> installation and the core API in English; the API surface itself is English-named.

## Install

```bash
pip install GSpreadManager                # core (native client, google-auth only)

pip install "GSpreadManager[gspread]"     # optional gspread backend
pip install "GSpreadManager[pandas]"      # pandas DataFrames
pip install "GSpreadManager[polars]"      # polars DataFrames
pip install "GSpreadManager[pydantic]"    # Pydantic v2 row models
pip install "GSpreadManager[async]"       # async API (httpx)
```

## Quick start

```python
from gspreadmanager import SheetManager

mgr = SheetManager("My Spreadsheet", json_google_file="credentials.json")
ws = mgr.worksheet("Sheet1")          # immutable handle, no global "active sheet"

rows = ws.read(output_format="dict")  # list / dict / pandas
ws.append([["Ana", "ana@example.com"]])
ws.upsert([{"id": "2", "name": "Luisa"}], key="id")   # sheet-as-table
```

### Typed row models (dataclasses or Pydantic)

```python
from dataclasses import dataclass

@dataclass
class Person:
    id: int
    name: str

ws.ensure_schema(Person)              # create or validate the header (drift report)
people = ws.read_as(Person)           # validated, type-coerced instances
ws.upsert_models(people, key="id")
```

### Large sheets (streaming)

```python
for record in ws.iter_records(page_size=2000):   # lazy, one request per page
    process(record)
```

### Async (real asyncio, not a threadpool)

```python
from gspreadmanager import AsyncSheetManager

async with AsyncSheetManager("My Spreadsheet", json_google_file="creds.json") as mgr:
    ws = await mgr.worksheet("Sheet1")
    rows = await ws.read(output_format="dict")
    async for record in ws.iter_records(page_size=2000):
        ...
```

### Testing without network

```python
from gspreadmanager.testing import InMemoryBackend, AsyncInMemoryBackend

backend = InMemoryBackend()
backend.add_spreadsheet("Doc", {"Sheet1": [["id", "name"], ["1", "Ana"]]})
mgr = backend.manager("Doc")          # a real SheetManager, no network
```

## Feature highlights

- Native REST client (default) **or** gspread, behind the same ports — contract-tested.
- Built-in resilience: retries with backoff, proactive rate limiting (token bucket),
  read cache with TTL/LRU and range-precise invalidation, per-request timeouts,
  automatic chunking of large writes.
- Sheet-as-table: `upsert` by key, `update_where`/`delete_where`, find-or-create.
- Formatting, data validation, conditional formatting, charts, pivot tables, banding,
  notes, named/protected ranges, developer metadata, find/replace, CSV import/export.
- Typed row models (dataclasses / Pydantic v2) with schema validation and drift reports.
- pandas **or** polars DataFrames, CLI (`gspreadmanager read/append/export/share`),
  strict typing (`py.typed`, mypy --strict), domain-driven hexagonal architecture.
