"""Tests del CLI (``gspreadmanager.cli``) con el backend en memoria, sin red."""

import argparse
import json
from typing import Any

import pytest
from gspreadmanager import SheetManager
from gspreadmanager.cli import _build_manager, build_parser, main
from gspreadmanager.testing import InMemoryBackend


@pytest.fixture
def factory():
    backend = InMemoryBackend()
    backend.add_spreadsheet("Doc", {"H": [["nombre", "edad"], ["Ana", "30"], ["Bob", "25"]]})
    spreadsheet = backend.client.open("Doc")

    def make(_args: argparse.Namespace) -> SheetManager:
        return SheetManager("Doc", sheets_client=backend.client)

    make.spreadsheet = spreadsheet  # type: ignore[attr-defined]
    return make


class TestRead:
    def test_csv(self, factory, capsys):
        assert main(["read", "Doc", "H"], manager_factory=factory) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines == ["nombre,edad", "Ana,30", "Bob,25"]

    def test_tsv(self, factory, capsys):
        main(["read", "Doc", "H", "--format", "tsv"], manager_factory=factory)
        assert "Ana\t30" in capsys.readouterr().out

    def test_json(self, factory, capsys):
        main(["read", "Doc", "H", "--format", "json"], manager_factory=factory)
        assert json.loads(capsys.readouterr().out) == [
            {"nombre": "Ana", "edad": "30"},
            {"nombre": "Bob", "edad": "25"},
        ]

    def test_skiprows(self, factory, capsys):
        main(["read", "Doc", "H", "--skiprows", "1"], manager_factory=factory)
        assert capsys.readouterr().out.splitlines() == ["Ana,30", "Bob,25"]


class TestAppend:
    def test_append_adds_row(self, factory, capsys):
        assert main(["append", "Doc", "H", "Cora", "40"], manager_factory=factory) == 0
        assert "Añadida 1 fila" in capsys.readouterr().out
        assert factory.spreadsheet.worksheet("H").get_all_values()[-1] == ["Cora", "40"]


class TestExport:
    def test_to_file(self, factory, capsys, tmp_path):
        out = tmp_path / "doc.csv"
        code = main(["export", "Doc", "--format", "csv", "-o", str(out)], manager_factory=factory)
        assert code == 0
        assert out.read_bytes() == b"nombre,edad\nAna,30\nBob,25"
        assert "Exportado" in capsys.readouterr().out

    def test_to_stdout(self, factory, capsysbinary):
        main(["export", "Doc", "--format", "csv"], manager_factory=factory)
        assert capsysbinary.readouterr().out == b"nombre,edad\nAna,30\nBob,25"

    def test_default_format_is_pdf(self, factory, capsysbinary):
        main(["export", "Doc"], manager_factory=factory)
        assert capsysbinary.readouterr().out.startswith(b"in-memory-export:application/pdf")


class TestShare:
    def test_share(self, factory, capsys):
        assert main(["share", "Doc", "x@y.com", "--role", "writer"], manager_factory=factory) == 0
        assert "Compartido con x@y.com (writer)" in capsys.readouterr().out
        assert factory.spreadsheet.list_permissions()[0]["emailAddress"] == "x@y.com"


class TestErrorsAndUsage:
    def test_unknown_doc_returns_1(self, capsys):
        backend = InMemoryBackend()

        def make(_args: argparse.Namespace) -> SheetManager:
            return SheetManager("Nope", sheets_client=backend.client)

        assert main(["read", "Nope", "H"], manager_factory=make) == 1
        assert "error:" in capsys.readouterr().err

    def test_no_command_prints_help(self, capsys):
        assert main([]) == 1
        assert "usage:" in capsys.readouterr().out

    def test_parser_builds(self):
        parser = build_parser()
        args = parser.parse_args(["read", "Doc", "H", "--format", "json"])
        assert args.command == "read"
        assert args.format == "json"


class TestBuildManager:
    """Verifica el ruteo de ``_build_manager`` sin construir un gestor real."""

    @pytest.fixture
    def recorder(self, monkeypatch):
        calls: list[tuple[str, Any, dict[str, Any]]] = []

        class FakeSM:
            def __init__(self, doc: Any = None, **kwargs: Any) -> None:
                calls.append(("init", doc, kwargs))

            @classmethod
            def open_by_url(cls, url: str, **kwargs: Any) -> "FakeSM":
                calls.append(("url", url, kwargs))
                return cls()

        monkeypatch.setattr("gspreadmanager.cli.SheetManager", FakeSM)
        return calls

    def _args(self, **kwargs: Any) -> argparse.Namespace:
        base = {"doc": "Doc", "json_file": None, "use_adc": False, "key": False}
        base.update(kwargs)
        return argparse.Namespace(**base)

    def test_by_name(self, recorder):
        _build_manager(self._args())
        assert recorder[0][0] == "init"
        assert recorder[0][1] == "Doc"

    def test_by_key(self, recorder):
        _build_manager(self._args(key=True))
        assert recorder[0][0] == "init"
        assert recorder[0][2]["key"] == "Doc"

    def test_by_url(self, recorder):
        _build_manager(self._args(doc="https://docs.google.com/spreadsheets/d/KEY/edit"))
        assert recorder[0][0] == "url"

    def test_passes_auth_options(self, recorder):
        _build_manager(self._args(json_file="creds.json", use_adc=True))
        kwargs = recorder[0][2]
        assert kwargs["json_google_file"] == "creds.json"
        assert kwargs["use_adc"] is True
