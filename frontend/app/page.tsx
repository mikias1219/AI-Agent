export default function HomePage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-2 px-6">
      <p
        className="text-sm font-medium tracking-[0.2em] text-[var(--muted)] uppercase"
        style={{ fontFamily: "var(--font-ui)" }}
      >
        Personal agent
      </p>
      <h1
        className="text-4xl font-semibold text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        AURA
      </h1>
    </main>
  );
}
