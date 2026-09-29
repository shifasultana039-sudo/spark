"""
Storage Provider abstraction for ReliefChain AI evidence uploads.
Provides a clean interface replaceable with Cloud Object Storage (S3, GCS, Azure Blob).
Enforces local filesystem segregation between public static uploads and private evidence artifacts.
"""

import os
import hashlib
import uuid
import mimetypes
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

# Resolve base directories safely
BACKEND_DIR = Path(__file__).resolve().parent.parent
STORAGE_BASE_DIR = BACKEND_DIR / "storage"


class StorageProvider:
    """
    Abstract storage interface designed for pluggable storage backends
    (e.g., LocalStorageProvider, S3StorageProvider, GCSStorageProvider).
    """

    def save_file(
        self,
        content: bytes,
        original_filename: str,
        is_private: bool = True
    ) -> Dict[str, Any]:
        """
        Saves binary content, calculates SHA-256 hash, and returns storage metadata.
        Returns: {
            'storage_key': safe identifier,
            'storage_path': absolute or relative path,
            'sha256_hash': '0x...',
            'file_size': int,
            'mime_type': str,
            'is_private': bool
        }
        """
        raise NotImplementedError

    def get_file(self, storage_key: str, is_private: bool = True) -> bytes:
        """Retrieves raw binary content by storage key."""
        raise NotImplementedError

    def get_file_path(self, storage_key: str, is_private: bool = True) -> Optional[Path]:
        """Returns local filesystem Path for streaming or inspection if available."""
        raise NotImplementedError

    def delete_file(self, storage_key: str, is_private: bool = True) -> bool:
        """Deletes a stored object."""
        raise NotImplementedError

    def get_file_hash(self, storage_key: str, is_private: bool = True) -> Optional[str]:
        """
        Returns the current SHA-256 hex digest of the stored file (without '0x' prefix),
        or None if the file cannot be located. Used by anomaly detection to detect
        post-upload file modifications (Signal 5 — MODIFIED_EVIDENCE).
        """
        raise NotImplementedError

    def save_bytes(self, content: bytes, original_filename: str) -> Tuple[str, str, int]:
        """Legacy method returning (file_url, sha256_hash, file_size) for backward compatibility."""
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem implementation of StorageProvider.
    Keeps private evidence documents isolated from public web directories.
    """

    def __init__(self, base_dir: Path = STORAGE_BASE_DIR):
        self.base_dir = Path(base_dir)
        self.public_dir = self.base_dir / "uploads"
        self.private_dir = self.base_dir / "private" / "evidence"
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.private_dir.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        content: bytes,
        original_filename: str,
        is_private: bool = True,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        sha256 = hashlib.sha256(content).hexdigest()
        ext = Path(original_filename).suffix.lower() or ".bin"
        if custom_key:
            safe_name = custom_key
        else:
            safe_name = f"{uuid.uuid4().hex[:12]}_{sha256[:8]}{ext}"

        target_dir = self.private_dir if is_private else self.public_dir
        target_path = target_dir / safe_name

        with open(target_path, "wb") as f:
            f.write(content)

        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"

        return {
            "storage_key": safe_name,
            "storage_path": str(target_path),
            "sha256_hash": f"0x{sha256}",
            "file_size": len(content),
            "mime_type": mime_type,
            "is_private": is_private
        }

    def find_file_by_hash(self, sha256_hash: str) -> Optional[Path]:
        """Finds stored file in private or public storage by sha256 hash or hex prefix."""
        clean_hash = sha256_hash.replace("0x", "").lower().strip()
        for d in [self.private_dir, self.public_dir]:
            if not d.exists():
                continue
            for p in d.iterdir():
                if p.is_file():
                    if clean_hash[:8] in p.name:
                        with open(p, "rb") as f:
                            if hashlib.sha256(f.read()).hexdigest() == clean_hash:
                                return p
        return None

    def get_file(self, storage_key: str, is_private: bool = True) -> bytes:
        p = self.get_file_path(storage_key, is_private)
        if not p or not p.exists():
            raise FileNotFoundError(f"Storage item '{storage_key}' not found.")
        with open(p, "rb") as f:
            return f.read()

    def get_file_path(self, storage_key: str, is_private: bool = True) -> Optional[Path]:
        target_dir = self.private_dir if is_private else self.public_dir
        target_path = target_dir / storage_key
        if target_path.exists():
            return target_path

        # Fallback search in other local directories
        for fallback_dir in [self.public_dir, self.private_dir, self.base_dir]:
            cand = fallback_dir / storage_key
            if cand.exists():
                return cand

        # Fallback: check if storage_key is a sha256 hash or contains one
        hash_cand = self.find_file_by_hash(storage_key)
        if hash_cand and hash_cand.exists():
            return hash_cand

        return None

    def delete_file(self, storage_key: str, is_private: bool = True) -> bool:
        p = self.get_file_path(storage_key, is_private)
        if p and p.exists():
            p.unlink()
            return True
        return False

    def get_file_hash(self, storage_key: str, is_private: bool = True) -> Optional[str]:
        """
        Returns the live SHA-256 hex digest of the stored file (no '0x' prefix).
        Returns None if the file cannot be found (no false positives).
        """
        p = self.get_file_path(storage_key, is_private)
        if not p or not p.exists():
            return None
        try:
            with open(p, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return None

    def save_bytes(self, content: bytes, original_filename: str) -> Tuple[str, str, int]:
        res = self.save_file(content, original_filename, is_private=False)
        return f"/api/storage/uploads/{res['storage_key']}", res["sha256_hash"], res["file_size"]


# Default shared instance
storage_provider = LocalStorageProvider()
