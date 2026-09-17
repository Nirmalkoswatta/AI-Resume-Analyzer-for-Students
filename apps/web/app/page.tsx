import { Analyzer } from "@/components/Analyzer";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-2xl font-semibold tracking-tight">Resume Analyzer for Students</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Find out whether an applicant tracking system can actually read your resume, which
          skills come through, and the specific changes worth making first.
        </p>
      </header>
      <Analyzer />
    </main>
  );
}
