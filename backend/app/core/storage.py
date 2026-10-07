"""Cliente de almacenamiento (Cloudflare R2, API compatible con S3) — `01-architecture §2`.

Subida directa; lectura con URLs firmadas de vida corta (`03-api-contract §1`).
"""
import uuid
from datetime import timedelta
from functools import lru_cache

import boto3

from app.core.config import get_settings
from app.core.errors import AppError

_URL_EXPIRACION_SEGUNDOS = int(timedelta(minutes=15).total_seconds())


@lru_cache
def _client():
    settings = get_settings()
    if not (settings.r2_endpoint and settings.r2_access_key_id and settings.r2_secret_access_key):
        return None
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
    )


def _require_client():
    client = _client()
    if client is None:
        raise AppError(
            "internal_error",
            "El almacenamiento de archivos (R2) no está configurado en este entorno.",
            500,
        )
    return client


def nueva_key(prefijo: str, nombre_original: str) -> str:
    extension = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else "bin"
    return f"{prefijo}/{uuid.uuid4()}.{extension}"


def subir_archivo(key: str, contenido: bytes, content_type: str) -> None:
    settings = get_settings()
    _require_client().put_object(
        Bucket=settings.r2_bucket, Key=key, Body=contenido, ContentType=content_type
    )


def url_firmada(key: str) -> str:
    settings = get_settings()
    return _require_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=_URL_EXPIRACION_SEGUNDOS,
    )


def eliminar_archivo(key: str) -> None:
    settings = get_settings()
    _require_client().delete_object(Bucket=settings.r2_bucket, Key=key)


def leer_archivo(key: str) -> bytes:
    settings = get_settings()
    return _require_client().get_object(Bucket=settings.r2_bucket, Key=key)["Body"].read()
