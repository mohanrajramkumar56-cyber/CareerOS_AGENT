"""
CareerOS Storage Service — local dev + S3-compatible production.

Never expose private file URLs publicly.
All access must be mediated through the API.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles


class StorageBackend:
    """Base storage interface."""

    async def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    async def load(self, key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    def get_url(self, key: str) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage for development."""

    def __init__(self, base_path: str = "./storage"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return key

    async def load(self, key: str) -> bytes:
        path = self.base / key
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> None:
        path = self.base / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        return f"/api/v1/resumes/artifacts/{key}"


class S3Storage(StorageBackend):
    """S3-compatible storage for production."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        import boto3

        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self.s3 = session.client("s3", endpoint_url=endpoint_url)
        self.bucket = bucket

    async def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            ),
        )
        return key

    async def load(self, key: str) -> bytes:
        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.s3.get_object(Bucket=self.bucket, Key=key),
        )
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3.delete_object(Bucket=self.bucket, Key=key),
        )

    def get_url(self, key: str) -> str:
        return f"/api/v1/resumes/artifacts/{key}"


def get_storage() -> StorageBackend:
    """Factory: returns configured storage backend."""
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "s3":
        return S3Storage(
            bucket=os.getenv("S3_BUCKET_NAME", "careeros"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            access_key=os.getenv("S3_ACCESS_KEY_ID") or None,
            secret_key=os.getenv("S3_SECRET_ACCESS_KEY") or None,
            region=os.getenv("S3_REGION", "us-east-1"),
        )
    return LocalStorage(base_path=os.getenv("STORAGE_LOCAL_PATH", "./storage"))
