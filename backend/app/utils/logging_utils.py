import time
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("driftsense")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class Timer:
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0

    def millis(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default
