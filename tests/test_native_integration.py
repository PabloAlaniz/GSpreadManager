"""Tests de integración del backend nativo contra la API real de Google.

Opcionales: requieren credenciales reales y se saltean si no están configuradas.

    export GSPREADMANAGER_TEST_CREDENTIALS=/ruta/al/service-account.json
    pytest -m integration --no-cov

La cuenta de servicio debe tener habilitadas la Sheets API y la Drive API. Los tests crean
un documento temporal, operan sobre él y lo borran al final (best effort).
"""

import os
import uuid

import pytest
from gspreadmanager import SheetManager

CREDENTIALS_ENV = "GSPREADMANAGER_TEST_CREDENTIALS"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get(CREDENTIALS_ENV),
        reason=f"Definí {CREDENTIALS_ENV} para correr la integración real.",
    ),
]


@pytest.fixture(scope="module")
def doc_key():
    """Crea un documento temporal con el backend nativo y lo borra al terminar."""
    creds_file = os.environ[CREDENTIALS_ENV]
    title = f"gspreadmanager-it-{uuid.uuid4().hex[:8]}"
    bootstrap = SheetManager(title, json_google_file=creds_file, backend="native")
    created = bootstrap.create_spreadsheet(title)
    key = created["spreadsheetId"]
    yield key
    bootstrap.delete_spreadsheet(key)


@pytest.fixture
def mgr(doc_key):
    creds_file = os.environ[CREDENTIALS_ENV]
    return SheetManager.open_by_key(doc_key, json_google_file=creds_file, backend="native")


def test_write_and_read_roundtrip(mgr):
    ws = mgr.worksheet()
    ws.write([["nombre", "edad"], ["Ana", "30"]], "A1")
    assert ws.read() == [["nombre", "edad"], ["Ana", "30"]]


def test_append_and_structure(mgr):
    ws = mgr.worksheet()
    ws.append([["Luis", "41"]])
    assert ws.read()[-1] == ["Luis", "41"]


def test_create_and_delete_sheet(mgr):
    created = mgr.create_sheet("Temp", rows=5, cols=3)
    assert created.title == "Temp"
    mgr.delete_sheet("Temp")
