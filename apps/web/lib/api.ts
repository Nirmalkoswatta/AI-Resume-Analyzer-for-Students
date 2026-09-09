import type { AnalysisResult, ErrorResponse } from "@resume/schema";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export class AnalysisFailed extends Error {
  constructor(
    readonly status: number,
    readonly detail: ErrorResponse,
  ) {
    super(detail.message);
    this.name = "AnalysisFailed";
  }
}

function apiUrl(path: string): string {
  const base = process.env.RESUME_API_URL ?? DEFAULT_API_URL;
  return new URL(path, base).toString();
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return typeof value === "object" && value !== null && "code" in value && "message" in value;
}

export async function requestAnalysis(
  form: FormData,
  forwardedFor: string | null,
): Promise<AnalysisResult> {
  const response = await fetch(apiUrl("/v1/analyze"), {
    method: "POST",
    body: form,
    headers: forwardedFor ? { "x-forwarded-for": forwardedFor } : undefined,
    cache: "no-store",
  });

  const payload: unknown = await response.json();

  if (!response.ok) {
    const detail: ErrorResponse = isErrorResponse(payload)
      ? payload
      : {
          code: "internal_error",
          message: "The analysis service is unavailable.",
          remediation: "Try again in a moment.",
        };
    throw new AnalysisFailed(response.status, detail);
  }

  return payload as AnalysisResult;
}
