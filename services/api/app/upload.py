from fastapi import UploadFile

from app.config import Settings
from app.errors import EmptyDocumentError, FileTooLargeError, UnsupportedMediaTypeError

PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = frozenset({"application/pdf", "application/x-pdf"})


def has_pdf_signature(payload: bytes) -> bool:
    return payload.startswith(PDF_MAGIC)


async def read_validated_upload(upload: UploadFile, settings: Settings) -> bytes:
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaTypeError

    payload = await upload.read(settings.max_upload_bytes + 1)

    if not payload:
        raise EmptyDocumentError
    if len(payload) > settings.max_upload_bytes:
        raise FileTooLargeError
    if not has_pdf_signature(payload):
        raise UnsupportedMediaTypeError

    return payload
