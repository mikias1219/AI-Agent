export default function HomePage() {
  return (
    <section className="flex flex-col items-center justify-center gap-2 px-6 py-16">
      <p
        className="text-sm font-medium tracking-[0.2em] text-[var(--muted)] uppercase"
        style={{ fontFamily: "var(--font-ui)" }}
      >
        Personal agent
      </p>
      <h2
        className="text-4xl font-semibold text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        AURA
      </h2>
    </section>
  );
}
