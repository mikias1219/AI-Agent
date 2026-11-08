import ModulePlaceholder from '../../../shared/components/ui/ModulePlaceholder.jsx';

export default function InboxPage({ go }) {
  return (
    <ModulePlaceholder
      title="Unified Inbox"
      description="Authorized email and messaging summaries will live here. Telegram is available now as a top-level Assist module."
      action={
        <button className="primary" onClick={() => go('telegram')}>
          Open Telegram
        </button>
      }
    />
  );
}
