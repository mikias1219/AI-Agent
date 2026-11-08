import PageHeading from './PageHeading.jsx';
import EmptyState from './EmptyState.jsx';

export default function ModulePlaceholder({
  eyebrow = 'Coming in a later phase',
  title,
  description,
  action,
}) {
  return (
    <>
      <PageHeading eyebrow={eyebrow} title={title}>
        {description}
      </PageHeading>
      <EmptyState title="Not available yet">
        This module is part of the AURA roadmap. It is not connected to live data in Phase 1.
      </EmptyState>
      {action && <div className="mt-5">{action}</div>}
    </>
  );
}
