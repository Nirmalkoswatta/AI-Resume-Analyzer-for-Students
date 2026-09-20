import type { ReactNode } from "react";

export function Card({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border-subtle bg-panel p-6 shadow-sm">
      <header className="mb-4">
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {description ? <p className="mt-1 text-sm text-ink-muted">{description}</p> : null}
      </header>
      {children}
    </section>
  );
}
