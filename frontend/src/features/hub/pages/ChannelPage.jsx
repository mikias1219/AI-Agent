import HubTabBar from '../components/HubTabBar.jsx';
import { CHANNEL_TABS, WORKFLOW_STATUSES, channelById } from '../channels.js';
import { channelPath } from '../routes.js';
import HubBoardPage from './HubBoardPage.jsx';
import HubRoadmapPage from './HubRoadmapPage.jsx';
import TelegramAgentPanel from '../components/TelegramAgentPanel.jsx';
import GoogleChannelPanel from '../components/GoogleChannelPanel.jsx';

export default function ChannelPage({
  channelId,
  tab,
  go,
  hub,
  status,
  approvals,
  decide,
  telegramActivity,
  refreshWorkspace,
  notify,
  openConversation,
}) {
  const channel = channelById(channelId);
  if (!channel) {
    return (
      <p className="text-sm text-slate-600">
        Unknown channel.{' '}
        <button type="button" className="text-indigo-600" onClick={() => go('dashboard')}>
          Back to dashboard
        </button>
      </p>
    );
  }

  const pending = (approvals || []).filter((a) => a.actionable);

  // Telegram: keep the page simple — Guide + Approvals only.
  if (channel.id === 'telegram') {
    const simpleTabs = [
      {
        id: 'skills',
        label: 'Guide',
        active: tab === 'skills' || tab === 'board' || tab === 'roadmap',
        onClick: () => go(channelPath('telegram', 'skills')),
      },
      {
        id: 'requests',
        label: 'Approvals',
        active: tab === 'requests',
        count: pending.length || undefined,
        onClick: () => go(channelPath('telegram', 'requests')),
      },
    ];
    const showGuide = tab !== 'requests';
    return (
      <div className="mx-auto max-w-3xl">
        <header className="mb-5">
          <div className="flex items-center gap-2">
            <span className={`size-2.5 rounded-full ${channel.color}`} />
            <h1 className="text-xl font-semibold text-slate-900">Telegram</h1>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Message your bot. AURA answers with the same agent as My Agent.
          </p>
        </header>
        <HubTabBar label="Telegram" tabs={simpleTabs} />
        {showGuide ? (
          <TelegramAgentPanel
            telegram={status?.telegram}
            events={telegramActivity}
            refresh={refreshWorkspace}
            notify={notify}
            openConversation={openConversation}
            goAgent={() => go('agent')}
          />
        ) : (
          <RequestsPanel approvals={pending} decide={decide} notify={notify} />
        )}
      </div>
    );
  }

  const skills = (hub.skills || []).filter((s) => s.channelId === channelId);
  const tabs = CHANNEL_TABS.map((t) => ({
    id: t.id,
    label: t.label,
    active: tab === t.id,
    count: t.id === 'requests' ? pending.length : undefined,
    onClick: () => go(channelPath(channelId, t.id)),
  }));

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-4">
        <div className="flex items-center gap-3">
          <span className={`size-3 rounded-full ${channel.color}`} />
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {channel.fullName || channel.name}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">{channel.description}</p>
          </div>
        </div>
        {!channel.live && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Coming later — this channel is listed for planning only. No fake activity.
          </div>
        )}
      </header>

      <HubTabBar label={`${channel.name} tabs`} tabs={tabs} />

      {tab === 'skills' && (
        <SkillsPanel channel={channel} skills={skills} hub={hub} status={status} notify={notify} />
      )}
      {tab === 'requests' && <RequestsPanel approvals={pending} decide={decide} notify={notify} />}
      {tab === 'board' && <HubBoardPage hub={hub} channelId={channelId} notify={notify} />}
      {tab === 'roadmap' && (
        <HubRoadmapPage hub={hub} channelId={channelId} go={go} notify={notify} />
      )}
    </div>
  );
}

function SkillsPanel({ channel, skills, hub, status, notify }) {
  async function setStatus(id, next) {
    try {
      await hub.updateSkills(
        (hub.skills || []).map((s) => (s.id === id ? { ...s, status: next } : s)),
      );
    } catch (e) {
      notify?.(e.message);
    }
  }

  return (
    <div className="space-y-6">
      {channel.live && channel.group === 'google' && (
        <GoogleChannelPanel
          channel={channel}
          google={hub.google}
          notify={notify}
          refresh={hub.refresh}
        />
      )}

      {!channel.live && (
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="text-sm font-semibold text-slate-900">Planned later</h2>
          <ul className="mt-3 space-y-2">
            {(channel.plannedSkills || []).map((name) => (
              <li
                key={name}
                className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700"
              >
                <span>{name}</span>
                <span className="text-xs text-slate-400">Later</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {channel.live && channel.group === 'google' && skills.length > 0 && (
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="text-sm font-semibold text-slate-900">Skills</h2>
          <ul className="mt-3 divide-y divide-slate-100">
            {skills.map((skill) => {
              const st =
                WORKFLOW_STATUSES.find((s) => s.id === skill.status) || WORKFLOW_STATUSES[0];
              return (
                <li
                  key={skill.id}
                  className="flex flex-wrap items-start justify-between gap-3 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-slate-900">{skill.name}</div>
                    <p className="mt-1 text-xs text-slate-500">{skill.humanControl}</p>
                  </div>
                  <select
                    className="rounded border border-slate-200 bg-white px-2 py-1 text-xs"
                    value={skill.status}
                    onChange={(e) => setStatus(skill.id, e.target.value)}
                    aria-label={`Status for ${skill.name}`}
                  >
                    {WORKFLOW_STATUSES.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${st.style}`}>
                    {st.label}
                  </span>
                </li>
              );
            })}
          </ul>
          {!status && null}
        </section>
      )}
    </div>
  );
}

function RequestsPanel({ approvals, decide, notify }) {
  if (!approvals.length) {
    return (
      <div className="rounded-2xl bg-white p-8 text-center ring-1 ring-slate-200">
        <p className="text-sm font-medium text-slate-900">Nothing to approve</p>
        <p className="mt-1 text-sm text-slate-500">
          When the agent needs permission for a tool, it shows up here with Approve / Deny.
        </p>
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {approvals.map((a) => (
        <li key={a.id} className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
          <div className="font-medium text-slate-900">{a.tool_name}</div>
          <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            {JSON.stringify(a.arguments || a.arguments_json || {}, null, 2)}
          </pre>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white"
              onClick={async () => {
                try {
                  await decide(a.id, true);
                } catch (e) {
                  notify?.(e.message);
                }
              }}
            >
              Approve
            </button>
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700"
              onClick={async () => {
                try {
                  await decide(a.id, false);
                } catch (e) {
                  notify?.(e.message);
                }
              }}
            >
              Deny
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
