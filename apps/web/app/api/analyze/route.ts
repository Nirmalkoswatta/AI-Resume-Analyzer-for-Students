import { NextResponse } from "next/server";

import { AnalysisFailed, requestAnalysis } from "@/lib/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<NextResponse> {
  const form = await request.formData();
  const forwardedFor = request.headers.get("x-forwarded-for");

  try {
    return NextResponse.json(await requestAnalysis(form, forwardedFor));
  } catch (error) {
    if (error instanceof AnalysisFailed) {
      return NextResponse.json(error.detail, { status: error.status });
    }

    return NextResponse.json(
      {
        code: "internal_error",
        message: "The analysis service could not be reached.",
        remediation: "Check that the API is running, then try again.",
      },
      { status: 502 },
    );
  }
}
