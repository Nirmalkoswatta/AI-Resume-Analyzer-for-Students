import type { ErrorResponse } from "@resume/schema";

import { ACCEPTED_MIME_TYPE, MAX_UPLOAD_BYTES } from "@/lib/constants";

export function localValidationError(file: File | null): ErrorResponse | null {
  if (!file) {
    return {
      code: "empty_document",
      message: "Choose a resume PDF to analyze.",
      remediation: null,
    };
  }

  if (file.type !== ACCEPTED_MIME_TYPE) {
    return {
      code: "unsupported_media_type",
      message: "Only PDF resumes are supported.",
      remediation: "Export your document as a PDF and try again.",
    };
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      code: "file_too_large",
      message: "That file is larger than the 5 MB limit.",
      remediation: "Export again at a lower image quality, or remove embedded images.",
    };
  }

  return null;
}
