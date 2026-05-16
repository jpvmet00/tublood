from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from app.schemas.bank_movement import MovimientoCanonical


class BankAdapter(ABC):
    """Base contract for all bank file adapters."""

    banco: str = ""

    @abstractmethod
    def parse(self, filepath: Path) -> List[MovimientoCanonical]:
        """Read a bank file and return canonical movement records (credits only)."""
        ...

    @abstractmethod
    def validate_file(self, filepath: Path) -> bool:
        """Return True if the file format matches this adapter."""
        ...

    @abstractmethod
    def get_account_info(self, filepath: Path) -> Dict[str, Optional[str]]:
        """Return account metadata for user confirmation.

        Returns keys: banco, cuenta, tipo, moneda, descripcion
        """
        ...
