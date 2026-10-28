"""
Storage Abstraction Layer

Supports local filesystem storage by default with a clean interface for
future S3-compatible storage backends.
"""

import os
import io
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from pathlib import Path
from ..config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes | BinaryIO, content_type: Optional[str] = None) -> str: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def get_path(self, key: str) -> Optional[str]: ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: Optional[str] = None):
        settings = get_settings()
        resolved = base_path or str(settings.storage_path_resolved)
        self.base_path = Path(resolved).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        safe_key = key.lstrip("/").lstrip("\\")
        target = (self.base_path / safe_key).resolve()
        try:
            target.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Invalid storage key: {key}")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def save(self, key: str, data, content_type: Optional[str] = None) -> str:
        target = self._resolve(key)
        if hasattr(data, "read"):
            with open(target, "wb") as f:
                chunk = data.read(8192)
                while chunk:
                    f.write(chunk)
                    chunk = data.read(8192)
        else:
            with open(target, "wb") as f:
                f.write(data)
        return key

    def load(self, key: str) -> bytes:
        target = self._resolve(key)
        with open(target, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).exists()
        except ValueError:
            return False

    def delete(self, key: str) -> bool:
        try:
            target = self._resolve(key)
            if target.exists() and target.is_file():
                target.unlink()
                return True
            return False
        except ValueError:
            return False

    def get_path(self, key: str) -> Optional[str]:
        try:
            return str(self._resolve(key))
        except ValueError:
            return None


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageBackend()
    if backend == "s3":
        raise NotImplementedError("S3 backend is a future extension.")
    raise ValueError(f"Unknown storage backend: {backend}")
