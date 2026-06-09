"""Test de contrato de los puertos: gspread vs cliente nativo.

Garantiza que **ambos** adaptadores (los de gspread y los nativos del spike) implementan la
superficie completa de cada puerto, de modo que son intercambiables. El comportamiento de
cada implementación se valida en sus tests dedicados (``test_*_service`` para los servicios,
``test_native_spike`` para el nativo); aquí se fija que ninguna implementación quede coja
respecto del puerto, y que mypy las acepte como tales (asignación a los tipos de puerto).
"""

from typing import Any
from unittest.mock import Mock

import pytest
from gspreadmanager.infrastructure.cache import (
    CachingClient,
    CachingSpreadsheet,
    CachingWorksheet,
    _Cache,
)
from gspreadmanager.infrastructure.gspread_adapters import GspreadSpreadsheet, GspreadWorksheet
from gspreadmanager.infrastructure.gspread_client import GspreadClientAdapter
from gspreadmanager.infrastructure.native.sheets_api_client import (
    NativeSpreadsheet,
    NativeWorksheet,
    SheetsApiClient,
)
from gspreadmanager.ports.sheets import ClientPort, SpreadsheetPort, WorksheetPort
from gspreadmanager.testing import InMemoryClient, InMemorySpreadsheet, InMemoryWorksheet


def _port_members(protocol: type) -> list[str]:
    """Devuelve los nombres de los miembros públicos declarados en un Protocol."""
    return sorted(name for name in vars(protocol) if not name.startswith("_"))


def _native_spreadsheet() -> NativeSpreadsheet:
    return NativeSpreadsheet(Mock(), "doc", [("Hoja1", 0)])


def _native_worksheet() -> NativeWorksheet:
    return NativeWorksheet(_native_spreadsheet(), Mock(), "doc", "Hoja1", 0)


def _memory_spreadsheet() -> InMemorySpreadsheet:
    ss = InMemorySpreadsheet("doc", "doc0")
    ss.seed("Hoja1", [["a"]])
    return ss


def _memory_worksheet() -> InMemoryWorksheet:
    return InMemoryWorksheet(_memory_spreadsheet(), "Hoja1", 0)


# (puerto, [implementación gspread, implementación nativa, in-memory, caching])
CONTRACT_CASES = [
    (WorksheetPort, GspreadWorksheet(Mock())),
    (WorksheetPort, _native_worksheet()),
    (WorksheetPort, _memory_worksheet()),
    (WorksheetPort, CachingWorksheet(_memory_worksheet(), _Cache())),
    (SpreadsheetPort, GspreadSpreadsheet(Mock())),
    (SpreadsheetPort, _native_spreadsheet()),
    (SpreadsheetPort, _memory_spreadsheet()),
    (SpreadsheetPort, CachingSpreadsheet(_memory_spreadsheet(), _Cache())),
    (ClientPort, GspreadClientAdapter(Mock())),
    (ClientPort, SheetsApiClient(Mock())),
    (ClientPort, InMemoryClient()),
    (ClientPort, CachingClient(InMemoryClient())),
]


@pytest.mark.parametrize(
    ("port", "implementation"),
    CONTRACT_CASES,
    ids=[f"{port.__name__}-{impl.__class__.__name__}" for port, impl in CONTRACT_CASES],
)
def test_implementation_exposes_full_port_surface(port: type, implementation: Any) -> None:
    missing = [member for member in _port_members(port) if not hasattr(implementation, member)]
    assert not missing, f"{implementation.__class__.__name__} no implementa: {missing}"


def test_ports_have_expected_members() -> None:
    # Sanidad: si se agrega un método al puerto, el contrato de arriba lo exige en ambos lados.
    assert "get_all_values" in _port_members(WorksheetPort)
    assert "values_get" in _port_members(SpreadsheetPort)
    assert "open" in _port_members(ClientPort)


def test_implementations_are_assignable_to_ports() -> None:
    # Verificado estructuralmente por mypy (ambos lados de cada puerto).
    gspread_ws: WorksheetPort = GspreadWorksheet(Mock())
    native_ws: WorksheetPort = _native_worksheet()
    gspread_ss: SpreadsheetPort = GspreadSpreadsheet(Mock())
    native_ss: SpreadsheetPort = _native_spreadsheet()
    gspread_client: ClientPort = GspreadClientAdapter(Mock())
    native_client: ClientPort = SheetsApiClient(Mock())
    memory_ws: WorksheetPort = _memory_worksheet()
    memory_ss: SpreadsheetPort = _memory_spreadsheet()
    memory_client: ClientPort = InMemoryClient()
    for impl in (
        gspread_ws,
        native_ws,
        gspread_ss,
        native_ss,
        gspread_client,
        native_client,
        memory_ws,
        memory_ss,
        memory_client,
    ):
        assert impl is not None
