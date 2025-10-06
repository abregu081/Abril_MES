import os
from datetime import datetime
from typing import Iterable, List

__all__ = ["LogManager"]

class LogManager:
    """Persist all SIM communications into PASS / FAIL sub‑folders.

    Usage:
        logger = LogManager(base_dir)
        logger.save(sn1, messages, is_pass)
    """

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        # Create PASS and FAIL folders if they don't exist yet
        for sub in ("PASS", "FAIL"):
            os.makedirs(os.path.join(self.base_dir, sub), exist_ok=True)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def save(self, sn1: str, messages: Iterable[str], is_pass: bool) -> str:
        """Save *messages* to <base_dir>/<PASS|FAIL>/<sn1>_<YYYYMMDD_HHMMSS>.txt.

        Args:
            sn1:        Serial number entered in SN1 (used for file name).
            messages:   Iterable with every line you want to persist.
            is_pass:    True → PASS, False → FAIL (selects sub‑folder).

        Returns:
            Full path to the file created (str).
        """
        folder = "PASS" if is_pass else "FAIL"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._sanitize_sn(sn1)}_{timestamp}.txt"
        full_path = os.path.join(self.base_dir, folder, filename)

        with open(full_path, "w", encoding="utf-8") as fh:
            for line in messages:
                fh.write(str(line).rstrip() + "\n")

        return full_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize_sn(sn: str) -> str:
        """Remove characters that are unsafe for file names."""
        return "".join(c for c in sn if c.isalnum() or c in ("-", "_"))
