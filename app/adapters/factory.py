from pathlib import Path
from typing import Dict, List, Optional
from app.adapters.base import BankAdapter
from app.adapters.macro import MacroAdapter
from app.adapters.galicia import GaliciaAdapter

_ADAPTERS: List[BankAdapter] = [
    GaliciaAdapter(),  # before Macro: Galicia has stricter signature detection
    MacroAdapter(),
]


def get_adapter(filepath: Path, banco: Optional[str] = None) -> BankAdapter:
    """Return the matching adapter for a file.

    If `banco` is given, look up by name first (fast path).
    Otherwise, probe each adapter's validate_file().
    """
    if banco:
        for adapter in _ADAPTERS:
            if adapter.banco == banco.lower():
                return adapter

    for adapter in _ADAPTERS:
        if adapter.validate_file(filepath):
            return adapter

    raise ValueError(
        f"No hay adaptador disponible para el archivo '{filepath.name}'. "
        "Banco no reconocido o formato incorrecto."
    )


def detect_banco(filepath: Path) -> Dict:
    """Detect bank and return account info without persisting anything."""
    adapter = get_adapter(filepath)
    info = adapter.get_account_info(filepath)
    info["banco_id"] = adapter.banco
    return info
