export default function SettingsPage({ user }) {
  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Account</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Workspace owner profile. Worker and privacy controls arrive in later phases.
        </p>
      </header>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Profile</h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-slate-500">Name</dt>
            <dd className="mt-1 font-medium text-slate-900">{user?.name || 'Unavailable'}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">Email</dt>
            <dd className="mt-1 font-medium text-slate-900">{user?.email || 'Unavailable'}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Agent runtime</h2>
        <p className="mt-2 text-sm text-slate-600">
          Inference uses local Ollama (and Hermes when configured). Paid cloud model APIs are not
          used. Configure tokens in <code className="rounded bg-slate-100 px-1">backend/.env</code>.
        </p>
        <ul className="mt-3 list-inside list-disc text-sm text-slate-600">
          <li>Telegram: TELEGRAM_BOT_TOKEN</li>
          <li>Google: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET</li>
        </ul>
      </section>

      <section className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Worker & privacy</h2>
        <p className="mt-2 text-sm text-slate-500">
          Local worker configuration, data export, and account deletion are planned for later
          phases. Nothing is invented here.
        </p>
      </section>
    </div>
  );
}
