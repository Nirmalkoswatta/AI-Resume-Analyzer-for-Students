import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { AnalysisResult } from "@resume/schema";

import { Analyzer } from "@/components/Analyzer";
import { ACCEPTED_MIME_TYPE, MAX_UPLOAD_BYTES } from "@/lib/constants";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const RESULT: AnalysisResult = {
  analysis_id: "a1",
  created_at: "2026-09-17T00:00:00Z",
  schema_version: "1.0.0",
  rubric_version: "2026.09.1",
  model_version: "fixture",
  document: {
    page_count: 2,
    word_count: 260,
    column_count: 1,
    machine_readable: true,
    has_tables: false,
    has_images: false,
    text_in_header_footer: false,
    font_families: ["Poppins"],
  },
  sections: [],
  missing_sections: [],
  skills: [],
  ats: { score: 100, rubric_version: "2026.09.1", checks: [] },
  fit: { predictions: [], job_description: null },
  suggestions: [],
};

function pdf(bytes = 1024): File {
  return new File([new Uint8Array(bytes)], "resume.pdf", { type: ACCEPTED_MIME_TYPE });
}

function attach(file: File): void {
  const input = screen.getByLabelText(/resume pdf/i);
  fireEvent.change(input, { target: { files: [file] } });
}

function submit(): void {
  fireEvent.click(screen.getByRole("button", { name: /analyze my resume/i }));
}

function stubFetch(response: Partial<Response> & { json: () => Promise<unknown> }): void {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, ...response }));
}

function sentBody(fetchMock: ReturnType<typeof vi.fn>): FormData {
  const call = fetchMock.mock.calls.at(0);
  if (!call) throw new Error("fetch was never called");
  return (call[1] as RequestInit).body as FormData;
}

test("submitting with no file shows a message and never calls the API", () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<Analyzer />);

  submit();

  expect(screen.getByRole("alert").textContent).toMatch(/choose a resume pdf/i);
  expect(fetchMock).not.toHaveBeenCalled();
});

test("an oversized file is rejected client side without a request", () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<Analyzer />);

  attach(pdf(MAX_UPLOAD_BYTES + 1));
  submit();

  expect(screen.getByRole("alert").textContent).toMatch(/larger than the 5 MB limit/i);
  expect(fetchMock).not.toHaveBeenCalled();
});

test("a successful analysis replaces the form with the report", async () => {
  stubFetch({ json: async () => RESULT });
  render(<Analyzer />);

  attach(pdf());
  submit();

  await waitFor(() => expect(screen.getByText(/Analyzed 2 pages/)).toBeDefined());
  expect(screen.queryByRole("button", { name: /analyze my resume/i })).toBeNull();
  expect(screen.getByRole("button", { name: /download as pdf/i })).toBeDefined();
});

test("the report says nothing was stored", async () => {
  stubFetch({ json: async () => RESULT });
  render(<Analyzer />);

  attach(pdf());
  submit();

  await waitFor(() => expect(screen.getByText(/Nothing was stored/i)).toBeDefined());
});

test("analyze another returns to an empty form", async () => {
  stubFetch({ json: async () => RESULT });
  render(<Analyzer />);

  attach(pdf());
  submit();
  await waitFor(() => expect(screen.getByText(/Analyzed 2 pages/)).toBeDefined());

  fireEvent.click(screen.getByRole("button", { name: /analyze another/i }));

  expect(screen.getByRole("button", { name: /analyze my resume/i })).toBeDefined();
  expect(screen.queryByRole("alert")).toBeNull();
});

test("an api error is shown with its remediation", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        code: "not_machine_readable",
        message: "This resume appears to be a scanned image.",
        remediation: "Export a PDF from your word processor instead.",
      }),
    }),
  );
  render(<Analyzer />);

  attach(pdf());
  submit();

  await waitFor(() => {
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toMatch(/scanned image/i);
    expect(alert.textContent).toMatch(/word processor/i);
  });
});

test("a network failure is reported rather than left hanging", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
  render(<Analyzer />);

  attach(pdf());
  submit();

  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toMatch(/could not reach/i),
  );
});

test("the submit button re-enables after a failure so the student can retry", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
  render(<Analyzer />);

  attach(pdf());
  submit();

  await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
  const button = screen.getByRole("button", { name: /analyze my resume/i });
  expect((button as HTMLButtonElement).disabled).toBe(false);
});

test("the job description is sent only when filled in", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => RESULT });
  vi.stubGlobal("fetch", fetchMock);
  render(<Analyzer />);

  attach(pdf());
  fireEvent.change(screen.getByLabelText(/target job description/i), {
    target: { value: "  Backend engineer using Python.  " },
  });
  submit();

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(sentBody(fetchMock).get("job_description")).toBe("Backend engineer using Python.");
});

test("a blank job description is omitted from the request", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => RESULT });
  vi.stubGlobal("fetch", fetchMock);
  render(<Analyzer />);

  attach(pdf());
  fireEvent.change(screen.getByLabelText(/target job description/i), {
    target: { value: "    " },
  });
  submit();

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(sentBody(fetchMock).get("job_description")).toBeNull();
});
