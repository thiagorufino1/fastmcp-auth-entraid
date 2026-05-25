from __future__ import annotations

from cryptography.fernet import Fernet

from app.auth.oauth_storage import build_oauth_client_storage


def test_build_oauth_client_storage_returns_encrypted_wrapper(tmp_path):
    storage = build_oauth_client_storage(
        storage_dir=tmp_path,
        encryption_key=Fernet.generate_key().decode(),
    )

    assert storage.__class__.__name__ == "FernetEncryptionWrapper"
