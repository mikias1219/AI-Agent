import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
export default function ContentStudioPage({ go }) {
  return (
    <>
      <PageHeading eyebrow="Coming after Telegram" title="Your content studio">
        A dedicated place for platform-specific drafts, review, and publishing.
      </PageHeading>
      <section className="card p-8">
        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">Planned</span>
        <h2 className="mt-5 text-xl font-semibold">
          Let’s get your agent working in Telegram first.
        </h2>
        <p className="mt-3 max-w-xl text-sm leading-7 text-slate-500">
          LinkedIn and Facebook accounts are not connected yet. This area will support drafting and
          explicit approval before publishing once those integrations are implemented.
        </p>
        <button className="primary mt-6" onClick={() => go('telegram')}>
          Open Telegram →
        </button>
      </section>
    </>
  );
}
