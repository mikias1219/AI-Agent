import { useEffect, useState } from 'react';
import { authRoutes, pageTitle } from './routing/navigation.js';
import { useHashRoute } from './routing/useHashRoute.js';
import { useWorkspaceData } from './useWorkspaceData.js';
import { useNotification } from '../shared/hooks/useNotification.js';
import { useAgentChat } from '../features/chat/hooks/useAgentChat.js';
import { useHubState } from '../features/hub/hooks/useHubState.js';
import { api } from '../shared/api/client.js';
import HubLayout from './layouts/HubLayout.jsx';
import Toast from '../shared/components/ui/Toast.jsx';
import AuthenticationPage from '../features/auth/pages/AuthenticationPage.jsx';
import ActivityPage from '../features/activity/pages/ActivityPage.jsx';
import TasksPage from '../features/tasks/pages/TasksPage.jsx';
import SettingsPage from '../features/settings/pages/SettingsPage.jsx';
import HubDashboardPage from '../features/hub/pages/HubDashboardPage.jsx';
import HubBoardPage from '../features/hub/pages/HubBoardPage.jsx';
import HubRoadmapPage from '../features/hub/pages/HubRoadmapPage.jsx';
import HubConnectionsPage from '../features/hub/pages/HubConnectionsPage.jsx';
import ChannelPage from '../features/hub/pages/ChannelPage.jsx';
import AgentPage from '../features/hub/pages/AgentPage.jsx';

export default function App() {
  const { route, page, channelId, tab, navigate } = useHashRoute();
  const { message, notify, dismiss } = useNotification();
  const [auth, setAuth] = useState(null);
  const [bootError, setBootError] = useState('');
  const [mobile, setMobile] = useState(false);
  const [prompt, setPrompt] = useState('');
  const workspace = useWorkspaceData(!!auth?.authenticated);
  const hub = useHubState(!!auth?.authenticated);
  const chat = useAgentChat(!!auth?.authenticated, notify, workspace.refresh);
  const name = auth?.user?.name || 'Friend';

  function go(next) {
    setMobile(false);
    navigate(next);
  }

  async function bootstrap() {
    setBootError('');
    try {
      const state = await api('/auth');
      setAuth(state);
      if (!state.authenticated) go(state.registered ? 'login' : 'register');
      else if (authRoutes.includes(page)) go('dashboard');
    } catch (e) {
      setBootError(e.message);
    }
  }

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    function expire() {
      setAuth((previous) => ({ ...previous, authenticated: false, user: null }));
      setPrompt('');
      go('login');
    }
    window.addEventListener('session-expired', expire);
    return () => window.removeEventListener('session-expired', expire);
  }, []);

  useEffect(() => {
    document.title = `${pageTitle(route)} · AURA`;
  }, [route]);

  async function logout() {
    try {
      await api('/logout', { method: 'POST' });
      setAuth((previous) => ({ ...previous, authenticated: false, user: null }));
      setPrompt('');
      go('login');
    } catch (e) {
      notify(e.message);
    }
  }

  function send(text) {
    go('agent');
    chat.send(text);
  }

  function ask(e) {
    e.preventDefault();
    if (!prompt.trim() || chat.busy) return;
    send(prompt.trim());
    setPrompt('');
  }

  async function openConversation(id) {
    go('agent');
    await chat.load(id);
  }

  async function decide(id, approve) {
    try {
      await api(`/approvals/${id}/decision`, { method: 'POST', body: { approve } });
      notify(approve ? 'Action approved.' : 'Action denied.');
      await workspace.refresh();
    } catch (e) {
      notify(e.message);
      workspace.refresh();
    }
  }

  if (!auth) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50 p-6">
        <section className="max-w-md rounded-2xl bg-white p-8 text-center ring-1 ring-slate-200">
          <h1 className="text-xl font-semibold text-slate-900">
            {bootError ? 'Your backend could not be reached.' : 'Opening AURA…'}
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-500">
            {bootError || 'Checking your session.'}
          </p>
          {bootError && (
            <>
              <p className="mt-3 text-xs leading-6 text-slate-400">
                Start personal-agent dashboard from backend/. For frontend development, keep the
                backend on port 8000.
              </p>
              <button
                type="button"
                className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
                onClick={bootstrap}
              >
                Try again
              </button>
            </>
          )}
        </section>
      </div>
    );
  }

  if (!auth.authenticated) {
    return (
      <>
        <AuthenticationPage
          mode={authRoutes.includes(page) ? page : 'login'}
          setMode={go}
          registered={auth.registered}
          emailRequired={auth.email_required}
          onAuthenticated={(user) => {
            setAuth((previous) => ({
              ...previous,
              authenticated: true,
              registered: true,
              user,
              email_required: !!user.email,
            }));
            go('dashboard');
          }}
        />
        <Toast message={message} onDismiss={dismiss} />
      </>
    );
  }

  const approvalCount = workspace.approvals.filter((a) => a.actionable).length;

  return (
    <>
      <HubLayout
        mobile={mobile}
        setMobile={setMobile}
        name={name}
        route={route}
        go={go}
        logout={logout}
        approvalCount={approvalCount}
      >
        {workspace.status?.model_setup?.model !== workspace.status?.model &&
          workspace.status?.model_setup?.status === 'ready_restart_required' && (
            <div
              role="status"
              className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
            >
              The faster model is ready. Restart the dashboard to use{' '}
              {workspace.status.model_setup.model}.
            </div>
          )}
        {(workspace.error || hub.error) && (
          <div
            role="alert"
            className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            {workspace.error || hub.error}{' '}
            <button
              type="button"
              onClick={() => {
                workspace.refresh();
                hub.refresh();
              }}
              className="ml-2 underline"
            >
              Retry
            </button>
          </div>
        )}

        {page === 'dashboard' && (
          <HubDashboardPage
            hub={hub}
            status={workspace.status}
            approvals={workspace.approvals}
            go={go}
            name={name}
            onAskAgent={(text) => {
              go('agent');
              send(text);
            }}
          />
        )}
        {page === 'board' && <HubBoardPage hub={hub} notify={notify} />}
        {page === 'roadmap' && <HubRoadmapPage hub={hub} go={go} notify={notify} />}
        {page === 'connections' && (
          <HubConnectionsPage hub={hub} status={workspace.status} go={go} notify={notify} />
        )}
        {page === 'channel' && (
          <ChannelPage
            channelId={channelId}
            tab={tab}
            go={go}
            hub={hub}
            status={workspace.status}
            approvals={workspace.approvals}
            decide={decide}
            telegramActivity={workspace.telegramActivity}
            refreshWorkspace={workspace.refresh}
            notify={notify}
          />
        )}
        {page === 'agent' && (
          <AgentPage
            chat={chat.messages}
            prompt={prompt}
            setPrompt={setPrompt}
            ask={ask}
            send={send}
            busy={chat.busy}
            conversations={workspace.conversations}
            loadConversation={openConversation}
            newConversation={chat.newConversation}
            sessionId={chat.sessionId}
            approvals={workspace.approvals}
            decide={decide}
            status={workspace.status}
            go={go}
            name={name}
          />
        )}
        {page === 'approvals' && (
          <TasksPage
            tasks={workspace.tasks}
            approvals={workspace.approvals}
            refresh={workspace.refresh}
            notify={notify}
            decide={decide}
            focusApprovals
          />
        )}
        {page === 'activity' && (
          <ActivityPage events={workspace.activity} refresh={workspace.refresh} notify={notify} />
        )}
        {(page === 'settings' || page === 'account') && <SettingsPage user={auth.user} />}
      </HubLayout>
      <Toast message={message} onDismiss={dismiss} />
    </>
  );
}
