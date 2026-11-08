import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
import EmptyState from '../../../shared/components/ui/EmptyState.jsx';

export default function SettingsPage({ user }) {
  return (
    <>
      <PageHeading eyebrow="System" title="Settings">
        Profile details from your workspace account. Worker and privacy controls arrive with later
        phases.
      </PageHeading>
      <section className="card space-y-4 p-6">
        <h2 className="font-semibold text-ink-100">Profile</h2>
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-ink-500">Name</dt>
            <dd className="mt-1 text-ink-100">{user?.name || 'Unavailable'}</dd>
          </div>
          <div>
            <dt className="text-ink-500">Email</dt>
            <dd className="mt-1 text-ink-100">{user?.email || 'Unavailable'}</dd>
          </div>
        </dl>
      </section>
      <section className="card mt-5 p-6">
        <h2 className="mb-4 font-semibold text-ink-100">Worker & privacy</h2>
        <EmptyState title="Not available yet">
          Local worker configuration, data export, and account deletion controls are planned for
          later phases. The worker is not connected in Phase 1.
        </EmptyState>
      </section>
    </>
  );
}
