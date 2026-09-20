"use client";

import { useState, type FormEvent } from "react";
import type { AnalysisResult, ErrorResponse } from "@resume/schema";

import { Report } from "@/components/report/Report";
import { MAX_JOB_DESCRIPTION_CHARS } from "@/lib/constants";
import { localValidationError } from "@/lib/validation";

type Status = "idle" | "analyzing";

export function Analyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationError = localValidationError(file);
    if (validationError || !file) {
      setError(validationError);
      return;
    }

    setStatus("analyzing");
    setError(null);

    const form = new FormData();
    form.set("resume", file);
    if (jobDescription.trim()) {
      form.set("job_description", jobDescription.trim());
    }

    try {
      const response = await fetch("/api/analyze", { method: "POST", body: form });
      const payload: unknown = await response.json();

      if (!response.ok) {
        setError(payload as ErrorResponse);
        setResult(null);
        return;
      }

      setResult(payload as AnalysisResult);
    } catch {
      setError({
        code: "internal_error",
        message: "Could not reach the analysis service.",
        remediation: "Check your connection and try again.",
      });
    } finally {
      setStatus("idle");
    }
  }

  function reset() {
    setResult(null);
    setError(null);
    setFile(null);
    setJobDescription("");
  }

  if (result) {
    return (
      <div className="space-y-6">
        <p role="status" className="sr-only">
          Analysis complete.
        </p>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-ink-muted">
            Analyzed {result.document.page_count}{" "}
            {result.document.page_count === 1 ? "page" : "pages"}, {result.document.word_count}{" "}
            words. Nothing was stored.
          </p>
          <div className="screen-only flex gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
            >
              Download as PDF
            </button>
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-border-subtle px-4 py-2 text-sm font-medium hover:bg-panel"
            >
              Analyze another
            </button>
          </div>
        </div>
        <Report result={result} />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" aria-busy={status === "analyzing"}>
      <p role="status" className="sr-only">
        {status === "analyzing" ? "Analyzing your resume." : ""}
      </p>
      <div>
        <label htmlFor="resume" className="mb-2 block text-sm font-medium">
          Resume PDF
        </label>
        <input
          id="resume"
          name="resume"
          type="file"
          accept="application/pdf"
          aria-describedby="resume-constraints"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full cursor-pointer rounded-lg border border-dashed border-border-subtle bg-panel p-6 text-sm file:mr-4 file:rounded-md file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
        />
        <p id="resume-constraints" className="mt-2 text-xs text-ink-muted">
          PDF only, up to 5 MB. Your resume is analyzed in memory and never saved.
        </p>
      </div>

      <div>
        <label htmlFor="job-description" className="mb-2 block text-sm font-medium">
          Target job description <span className="font-normal text-ink-muted">(optional)</span>
        </label>
        <textarea
          id="job-description"
          name="job_description"
          rows={5}
          maxLength={MAX_JOB_DESCRIPTION_CHARS}
          value={jobDescription}
          onChange={(event) => setJobDescription(event.target.value)}
          placeholder="Paste a job posting to see which required skills your resume is missing."
          className="w-full rounded-lg border border-border-subtle bg-panel p-3 text-sm"
        />
      </div>

      {error ? (
        <div role="alert" className="rounded-lg border border-critical/30 bg-critical/8 p-4">
          <p className="text-sm font-medium text-critical">{error.message}</p>
          {error.remediation ? (
            <p className="mt-1 text-sm text-ink-muted">{error.remediation}</p>
          ) : null}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={status === "analyzing"}
        className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white disabled:opacity-60"
      >
        {status === "analyzing" ? "Analyzing..." : "Analyze my resume"}
      </button>
    </form>
  );
}
