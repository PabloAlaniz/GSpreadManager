"""Interfaz de línea de comandos de GSpreadManager.

Expone las operaciones más comunes (``read``/``append``/``export``/``share``) sobre el
facade ``SheetManager``, sin dependencias extra (solo ``argparse``). El documento se indica
por nombre, por key (``--key``) o por URL (se detecta sola).

La construcción del gestor está aislada en ``_build_manager`` e inyectable vía
``manager_factory`` para poder testear el CLI con el backend en memoria, sin red.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from .domain.errors import GSpreadManagerError
from .domain.export import ExportFormat
from .facade import SheetManager

if TYPE_CHECKING:
    from collections.abc import Sequence

ManagerFactory = Callable[[argparse.Namespace], SheetManager]


def _build_manager(args: argparse.Namespace) -> SheetManager:
    """Construye un ``SheetManager`` a partir de las opciones de conexión del CLI."""
    common = {"json_google_file": args.json_file, "use_adc": args.use_adc}
    if args.key:
        return SheetManager(key=args.doc, **common)
    if args.doc.startswith(("http://", "https://")):
        return SheetManager.open_by_url(args.doc, **common)
    return SheetManager(args.doc, **common)


def _cmd_read(manager: SheetManager, args: argparse.Namespace) -> int:
    """Imprime el contenido de una hoja en CSV/TSV/JSON."""
    ws = manager.worksheet(args.sheet)
    if args.format == "json":
        records = ws.read(skiprows=args.skiprows, output_format="dict")
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        delimiter = "\t" if args.format == "tsv" else ","
        writer = csv.writer(sys.stdout, delimiter=delimiter)
        writer.writerows(ws.read(skiprows=args.skiprows))
    return 0


def _cmd_append(manager: SheetManager, args: argparse.Namespace) -> int:
    """Añade una fila con los valores dados al final de una hoja."""
    manager.worksheet(args.sheet).append([list(args.values)])
    print(f"Añadida 1 fila a '{args.sheet}'.")
    return 0


def _cmd_export(manager: SheetManager, args: argparse.Namespace) -> int:
    """Exporta el documento al formato dado (a un archivo o a stdout)."""
    data = manager.export(ExportFormat[args.format.upper()])
    if args.output:
        Path(args.output).write_bytes(data)
        print(f"Exportado a '{args.output}' ({len(data)} bytes).")
    else:
        sys.stdout.buffer.write(data)
    return 0


def _cmd_share(manager: SheetManager, args: argparse.Namespace) -> int:
    """Comparte el documento con un destinatario."""
    manager.share(args.email, role=args.role)
    print(f"Compartido con {args.email} ({args.role}).")
    return 0


def _add_connection_opts(parser: argparse.ArgumentParser) -> None:
    """Agrega las opciones de autenticación/apertura comunes a un subcomando."""
    parser.add_argument("doc", help="Nombre, key o URL del documento.")
    parser.add_argument("--json-file", help="Archivo JSON de service account.")
    parser.add_argument(
        "--use-adc", action="store_true", help="Usar Application Default Credentials."
    )
    parser.add_argument(
        "--key", action="store_true", help="Interpretar 'doc' como key (id de Drive)."
    )


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos del CLI con sus subcomandos."""
    parser = argparse.ArgumentParser(prog="gspreadmanager", description="Cliente de Google Sheets.")
    subparsers = parser.add_subparsers(dest="command")

    read = subparsers.add_parser("read", help="Leer una hoja.")
    _add_connection_opts(read)
    read.add_argument("sheet", help="Nombre de la pestaña.")
    read.add_argument("--format", choices=["csv", "tsv", "json"], default="csv")
    read.add_argument("--skiprows", type=int, default=0)
    read.set_defaults(handler=_cmd_read)

    append = subparsers.add_parser("append", help="Añadir una fila a una hoja.")
    _add_connection_opts(append)
    append.add_argument("sheet", help="Nombre de la pestaña.")
    append.add_argument("values", nargs="+", help="Valores de la fila a añadir.")
    append.set_defaults(handler=_cmd_append)

    export = subparsers.add_parser("export", help="Exportar el documento.")
    _add_connection_opts(export)
    export.add_argument(
        "--format", choices=[fmt.name.lower() for fmt in ExportFormat], default="pdf"
    )
    export.add_argument("--output", "-o", help="Archivo de salida (por defecto stdout).")
    export.set_defaults(handler=_cmd_export)

    share = subparsers.add_parser("share", help="Compartir el documento.")
    _add_connection_opts(share)
    share.add_argument("email", help="Email del destinatario.")
    share.add_argument("--role", choices=["reader", "writer", "owner"], default="reader")
    share.set_defaults(handler=_cmd_share)

    return parser


def main(argv: Sequence[str] | None = None, manager_factory: ManagerFactory | None = None) -> int:
    """Punto de entrada del CLI: parsea ``argv`` y ejecuta el subcomando."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    factory = manager_factory or _build_manager
    try:
        manager = factory(args)
        result: int = args.handler(manager, args)
    except GSpreadManagerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return result


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
