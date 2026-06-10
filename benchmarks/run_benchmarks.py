"""Benchmark de backends (gspread vs nativo) contra la API real de Google Sheets.

Uso:
    export GSPREADMANAGER_TEST_CREDENTIALS=/ruta/al/service-account.json
    python benchmarks/run_benchmarks.py [--rounds 5]

Crea un documento temporal, ejecuta cada operación ``--rounds`` veces por backend
(descartando la primera, que paga la autenticación) y reporta la mediana en una tabla
Markdown lista para pegar en ``docs/benchmarks.md``. Borra el documento al terminar.

Nota: los tiempos dependen de la red y de la región; compará tendencias, no valores
absolutos. La cuota de la API (60 lecturas-escrituras/min por usuario) limita ``--rounds``.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import uuid
from collections.abc import Callable

from gspreadmanager import SheetManager

CREDENTIALS_ENV = "GSPREADMANAGER_TEST_CREDENTIALS"

HEADER = [["nombre", "edad", "email"]]
ROWS = [[f"persona-{i}", str(20 + i % 50), f"p{i}@example.com"] for i in range(200)]


def time_operation(operation: Callable[[], object], rounds: int) -> float:
    """Mediana en segundos de ``rounds`` ejecuciones (la primera no cuenta: warm-up)."""
    samples: list[float] = []
    for i in range(rounds + 1):
        start = time.perf_counter()
        operation()
        elapsed = time.perf_counter() - start
        if i > 0:
            samples.append(elapsed)
    return statistics.median(samples)


def benchmark_backend(backend: str, creds_file: str, key: str, rounds: int) -> dict[str, float]:
    """Corre las operaciones del benchmark con el backend dado y devuelve sus medianas."""
    mgr = SheetManager.open_by_key(key, json_google_file=creds_file, backend=backend)
    ws = mgr.worksheet()

    # Estado base idéntico para ambos backends (fuera de la medición).
    ws.clear()
    ws.append(HEADER + ROWS)

    results: dict[str, float] = {}
    results["read completo (201 filas)"] = time_operation(ws.read, rounds)
    results["read rango (A1:C50)"] = time_operation(lambda: ws.read_range(1, 50, "A", "C"), rounds)
    results["append 1 fila"] = time_operation(lambda: ws.append([["x", "1", "x@x.com"]]), rounds)
    results["batch_update (50 filas)"] = time_operation(
        lambda: ws.batch_update([{"range": "A2:C51", "values": ROWS[:50]}]), rounds
    )
    results["update_cell"] = time_operation(lambda: ws.update_cell(1, 1, "nombre"), rounds)
    results["formato encabezado"] = time_operation(ws.format_header, rounds)
    return results


def main() -> int:
    """Punto de entrada del benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5, help="ejecuciones por operación")
    args = parser.parse_args()

    creds_file = os.environ.get(CREDENTIALS_ENV)
    if not creds_file:
        print(f"Definí {CREDENTIALS_ENV} con la ruta al JSON del service account.")
        return 1

    title = f"gspreadmanager-bench-{uuid.uuid4().hex[:8]}"
    bootstrap = SheetManager(title, json_google_file=creds_file, backend="native")
    created = bootstrap.create_spreadsheet(title)
    key = created["spreadsheetId"]
    print(f"Documento temporal: {title} ({key})\n")

    try:
        all_results = {
            backend: benchmark_backend(backend, creds_file, key, args.rounds)
            for backend in ("gspread", "native")
        }
    finally:
        bootstrap.delete_spreadsheet(key)

    operations = list(next(iter(all_results.values())))
    print("| Operación | gspread | nativo |")
    print("|---|---:|---:|")
    for op in operations:
        gs = all_results["gspread"][op]
        nat = all_results["native"][op]
        print(f"| {op} | {gs * 1000:.0f} ms | {nat * 1000:.0f} ms |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
