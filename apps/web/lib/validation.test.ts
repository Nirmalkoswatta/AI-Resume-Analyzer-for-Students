import assert from "node:assert/strict";
import { test } from "node:test";

import { ACCEPTED_MIME_TYPE, MAX_UPLOAD_BYTES } from "./constants.ts";
import { localValidationError } from "./validation.ts";

function pdfOfSize(bytes: number): File {
  return new File([new Uint8Array(bytes)], "resume.pdf", { type: ACCEPTED_MIME_TYPE });
}

test("a missing file is reported rather than uploaded", () => {
  assert.equal(localValidationError(null)?.code, "empty_document");
});

test("a non-PDF is rejected by type", () => {
  const png = new File([new Uint8Array(10)], "resume.png", { type: "image/png" });

  assert.equal(localValidationError(png)?.code, "unsupported_media_type");
});

test("a renamed non-PDF is still rejected, since the browser reports its real type", () => {
  const disguised = new File([new Uint8Array(10)], "resume.pdf", { type: "image/png" });

  assert.equal(localValidationError(disguised)?.code, "unsupported_media_type");
});

test("an oversized PDF is rejected", () => {
  assert.equal(localValidationError(pdfOfSize(MAX_UPLOAD_BYTES + 1))?.code, "file_too_large");
});

test("a PDF exactly at the limit is accepted, matching the API boundary", () => {
  assert.equal(localValidationError(pdfOfSize(MAX_UPLOAD_BYTES)), null);
});

test("a valid PDF passes", () => {
  assert.equal(localValidationError(pdfOfSize(1024)), null);
});

test("every rejection carries a message the student can act on", () => {
  const rejections = [
    localValidationError(null),
    localValidationError(new File([], "a.png", { type: "image/png" })),
    localValidationError(pdfOfSize(MAX_UPLOAD_BYTES + 1)),
  ];

  for (const rejection of rejections) {
    assert.ok(rejection);
    assert.ok(rejection.message.length > 0);
  }
});
