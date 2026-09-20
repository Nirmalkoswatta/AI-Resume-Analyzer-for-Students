import { NextResponse } from "next/server";
import type { AnalysisResult } from "@resume/schema";

import { requestReportPdf } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<NextResponse> {
  try {
    const result = (await request.json()) as AnalysisResult;
    const pdf = await requestReportPdf(result);

    return new NextResponse(pdf, {
      headers: {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="resume-report.pdf"',
      },
    });
  } catch {
    return NextResponse.json(
      {
        code: "internal_error",
        message: "The report could not be generated.",
        remediation: "Try again in a moment.",
      },
      { status: 502 },
    );
  }
}
