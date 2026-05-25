from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper


def build_oauth_client_storage(
    *,
    storage_dir: str | Path,
    encryption_key: str,
) -> AsyncKeyValue:
    resolved_dir = Path(storage_dir).expanduser()
    store = FileTreeStore(
        data_directory=resolved_dir,
        key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(resolved_dir),
        collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(resolved_dir),
    )
    return FernetEncryptionWrapper(key_value=store, fernet=Fernet(encryption_key))
