"""Fotos de evidencia del servicio: opcionales, para cualquier cliente, van adjuntas al correo de
la factura. Distintas del acuse (no lo sustituyen ni cambian "acuse pendiente")."""
import re
import uuid

from sqlmodel import Session, select

from app.core.errors import AppError
from app.core.models import utcnow
from app.modules.servicios.models import FotoEvidencia, Servicio

MIMES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "image/heif": "heif"}
MAX_BYTES = 10 * 1024 * 1024  # el frontend las reduce antes (~1600 px JPEG); esto es un tope
MAX_FOTOS = 10  # Resend acepta hasta 40 MB por correo


def _mime_real(contenido: bytes, declarado: str) -> str | None:
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG"):
        return "image/png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    if contenido[4:8] == b"ftyp" and declarado in {"image/heic", "image/heif"}:
        return declarado
    return None


def listar(session: Session, servicio_id: uuid.UUID) -> list[FotoEvidencia]:
    return list(
        session.exec(
            select(FotoEvidencia).where(FotoEvidencia.servicio_id == servicio_id).order_by(FotoEvidencia.subido_at)
        ).all()
    )


def agregar(session: Session, servicio_id: uuid.UUID, contenido: bytes, declarado: str, nombre: str | None, usuario_id) -> FotoEvidencia:
    from app.core.storage import subir_archivo

    if session.get(Servicio, servicio_id) is None:
        raise AppError("not_found", "Servicio no encontrado", 404)
    mime = _mime_real(contenido, declarado)
    if mime is None:
        raise AppError("validation_error", "La evidencia debe ser una foto (JPG, PNG, WEBP o HEIC)", 422,
                       details=[{"field": "file", "issue": "no_es_imagen"}])
    if len(contenido) > MAX_BYTES:
        raise AppError("validation_error", "La foto pesa más de 10 MB", 422, details=[{"field": "file", "issue": "muy_grande"}])
    if len(listar(session, servicio_id)) >= MAX_FOTOS:
        raise AppError("validation_error", f"Máximo {MAX_FOTOS} fotos de evidencia por servicio", 422,
                       details=[{"field": "file", "issue": "demasiadas"}])
    key = f"evidencias/{servicio_id}/{uuid.uuid4()}.{MIMES[mime]}"
    subir_archivo(key, contenido, mime)
    foto = FotoEvidencia(servicio_id=servicio_id, archivo_key=key, mime=mime, nombre_original=nombre,
                         subido_por=usuario_id, subido_at=utcnow())
    session.add(foto)
    session.commit()
    session.refresh(foto)
    return foto


def eliminar(session: Session, foto_id: uuid.UUID) -> None:
    from app.core.storage import eliminar_archivo

    foto = session.get(FotoEvidencia, foto_id)
    if foto is None:
        raise AppError("not_found", "Foto no encontrada", 404)
    key = foto.archivo_key
    session.delete(foto)
    session.commit()
    try:
        eliminar_archivo(key)
    except Exception:  # noqa: BLE001 — el registro ya se borró; limpiar R2 es best-effort
        pass


def foto_out(foto: FotoEvidencia) -> dict:
    from app.core.storage import url_firmada

    try:
        url = url_firmada(foto.archivo_key)
    except Exception:  # noqa: BLE001 — R2 no configurado en este entorno
        url = None
    return {"id": foto.id, "url": url, "mime": foto.mime, "nombre": foto.nombre_original, "subido_at": foto.subido_at}


def adjuntos_correo(session: Session, servicio_id: uuid.UUID, prefijo: str) -> list[dict]:
    """`<prefijo>_FOTO_1.jpg`, `_FOTO_2.jpg`… en el orden en que se subieron."""
    from app.core.storage import leer_archivo

    prefijo = re.sub(r"\.pdf$", "", prefijo)
    return [
        {"filename": f"{prefijo}_FOTO_{i}.{MIMES[f.mime]}", "content": list(leer_archivo(f.archivo_key))}
        for i, f in enumerate(listar(session, servicio_id), start=1)
    ]
