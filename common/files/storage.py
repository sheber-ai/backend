import asyncio
import os
from pathlib import Path
from typing import Protocol

from settings.files_settings import FilesSettings


class FileStorage(Protocol):
    """Blob store addressed by server-generated keys. Never sees user file names."""

    async def save(self, key: str, data: bytes) -> None: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalFileStorage:
    """Files under FILES_STORAGE_DIR, sharded by the first key characters."""

    def __init__(self, settings: FilesSettings) -> None:
        self._root = settings.storage_dir.resolve()

    def _path(self, key: str) -> Path:
        if not key.replace(".", "").isalnum():
            raise ValueError(f"Unsafe storage key {key!r}")
        return self._root / key[:2] / key[2:4] / key

    async def save(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._write, self._path(key), data)

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write then rename: readers never see half a file
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)
