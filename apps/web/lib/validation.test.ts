import { expect, test } from "vitest";

import { ACCEPTED_MIME_TYPE, MAX_UPLOAD_BYTES } from "./constants";
import { localValidationError } from "./validation";

function pdfOfSize(bytes: number): File {
  return new File([new Uint8Array(bytes)], "resume.pdf", { type: ACCEPTED_MIME_TYPE });
}

test("a missing file is reported rather than uploaded", () => {
  expect(localValidationError(null)?.code).toBe("empty_document");
});

test("a non-PDF is rejected by type", () => {
  const png = new File([new Uint8Array(10)], "resume.png", { type: "image/png" });

  expect(localValidationError(png)?.code).toBe("unsupported_media_type");
});

test("a renamed non-PDF is still rejected, since the browser reports its real type", () => {
  const disguised = new File([new Uint8Array(10)], "resume.pdf", { type: "image/png" });

  expect(localValidationError(disguised)?.code).toBe("unsupported_media_type");
});

test("an oversized PDF is rejected", () => {
  expect(localValidationError(pdfOfSize(MAX_UPLOAD_BYTES + 1))?.code).toBe("file_too_large");
});

test("a PDF exactly at the limit is accepted, matching the API boundary", () => {
  expect(localValidationError(pdfOfSize(MAX_UPLOAD_BYTES))).toBeNull();
});

test("a valid PDF passes", () => {
  expect(localValidationError(pdfOfSize(1024))).toBeNull();
});

test("every rejection carries a message the student can act on", () => {
  const rejections = [
    localValidationError(null),
    localValidationError(new File([], "a.png", { type: "image/png" })),
    localValidationError(pdfOfSize(MAX_UPLOAD_BYTES + 1)),
  ];

  for (const rejection of rejections) {
    expect(rejection).not.toBeNull();
    expect(rejection!.message.length).toBeGreaterThan(0);
  }
});
