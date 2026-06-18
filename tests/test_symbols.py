from __future__ import annotations

from pathlib import Path

import pytest

from pyocd_debug_mcp.services import symbols
from pyocd_debug_mcp.target_errors import SymbolLookupError


class FakeSymbol:
    def __init__(self, name: str, address: int, size: int, type_name: str) -> None:
        self.name = name
        self.address = address
        self.size = size
        self.type = type_name


class FakeDecoder:
    def __init__(self, symbol: FakeSymbol | None) -> None:
        self._symbol = symbol

    def get_symbol_for_name(self, name: str) -> FakeSymbol | None:
        if self._symbol is not None and self._symbol.name == name:
            return self._symbol
        return None


class FakeELF:
    def __init__(self, path: str, symbol: FakeSymbol | None) -> None:
        self.path = path
        self.symbol_decoder = FakeDecoder(symbol)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_resolve_symbol_returns_backend_neutral_shape(monkeypatch, tmp_path: Path) -> None:
    elf_path = tmp_path / "firmware.elf"
    elf_path.write_text("placeholder", encoding="utf-8")
    fake_symbol = FakeSymbol("stage1_known_value", 0x20000010, 4, "STT_OBJECT")
    captured: dict[str, FakeELF] = {}

    def fake_loader(path: str) -> FakeELF:
        elf = FakeELF(path, fake_symbol)
        captured["elf"] = elf
        return elf

    monkeypatch.setattr(symbols, "ELFBinaryFile", fake_loader)

    resolved = symbols.resolve_symbol(elf_path, "stage1_known_value")

    assert resolved.name == "stage1_known_value"
    assert resolved.address == 0x20000010
    assert resolved.size == 4
    assert resolved.type == "STT_OBJECT"
    assert resolved.value_u32 is None
    assert captured["elf"].closed is True


def test_resolve_symbol_raises_for_missing_symbol(monkeypatch, tmp_path: Path) -> None:
    elf_path = tmp_path / "firmware.elf"
    elf_path.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(symbols, "ELFBinaryFile", lambda path: FakeELF(path, None))

    with pytest.raises(SymbolLookupError, match="missing_symbol"):
        symbols.resolve_symbol(elf_path, "missing_symbol")
