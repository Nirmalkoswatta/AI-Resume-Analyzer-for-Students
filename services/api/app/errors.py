from app.schemas.enums import AnalysisErrorCode


class AnalysisError(Exception):
    code: AnalysisErrorCode = AnalysisErrorCode.INTERNAL_ERROR
    status_code: int = 500
    message: str = "The resume could not be analyzed."
    remediation: str | None = None

    def __init__(self, message: str | None = None, remediation: str | None = None) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        if remediation is not None:
            self.remediation = remediation


class FileTooLargeError(AnalysisError):
    code = AnalysisErrorCode.FILE_TOO_LARGE
    status_code = 413
    message = "That file is larger than the 5 MB limit."
    remediation = "Export your resume again at a lower image quality, or remove embedded images."


class UnsupportedMediaTypeError(AnalysisError):
    code = AnalysisErrorCode.UNSUPPORTED_MEDIA_TYPE
    status_code = 415
    message = "Only PDF resumes are supported."
    remediation = "Export your document as a PDF and upload it again."


class EncryptedPdfError(AnalysisError):
    code = AnalysisErrorCode.ENCRYPTED_PDF
    status_code = 422
    message = "This PDF is password protected, so its contents cannot be read."
    remediation = "Remove the password and upload the file again."


class CorruptPdfError(AnalysisError):
    code = AnalysisErrorCode.CORRUPT_PDF
    status_code = 422
    message = "This file is not a readable PDF."
    remediation = "Open the file to confirm it works, then export a fresh PDF."


class TooManyPagesError(AnalysisError):
    code = AnalysisErrorCode.TOO_MANY_PAGES
    status_code = 422
    message = "This document has more pages than a resume should."
    remediation = "Upload only your resume, not a combined portfolio or transcript."


class NotMachineReadableError(AnalysisError):
    code = AnalysisErrorCode.NOT_MACHINE_READABLE
    status_code = 422
    message = "This resume appears to be a scanned image with no selectable text."
    remediation = (
        "Applicant tracking systems cannot read scanned resumes. "
        "Export a PDF directly from your word processor instead of scanning a printout."
    )


class EmptyDocumentError(AnalysisError):
    code = AnalysisErrorCode.EMPTY_DOCUMENT
    status_code = 422
    message = "No text could be extracted from this document."
    remediation = "Check that you uploaded the correct file."
