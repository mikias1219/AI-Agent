import { useEffect, useState } from 'react';
import { navItems, authRoutes } from './routing/navigation.js';
import { useHashRoute } from './routing/useHashRoute.js';
import { useWorkspaceData } from './useWorkspaceData.js';
import { useNotification } from '../shared/hooks/useNotification.js';
import { useAgentChat } from '../features/chat/hooks/useAgentChat.js';
import { api } from '../shared/api/client.js';
import DashboardLayout from './layouts/DashboardLayout.jsx';
import Toast from '../shared/components/ui/Toast.jsx';
import AuthenticationPage from '../features/auth/pages/AuthenticationPage.jsx';
import HomePage from '../features/home/pages/HomePage.jsx';
import ChatPage from '../features/chat/pages/ChatPage.jsx';
import ContentStudioPage from '../features/content-studio/pages/ContentStudioPage.jsx';
import ConnectionsPage from '../features/connections/pages/ConnectionsPage.jsx';
import ActivityPage from '../features/activity/pages/ActivityPage.jsx';
import TelegramPage from '../features/telegram/pages/TelegramPage.jsx';
import TasksPage from '../features/tasks/pages/TasksPage.jsx';

export default function App() {
  const { page, navigate } = useHashRoute();
  const { message, notify, dismiss } = useNotification();
  const [auth, setAuth] = useState(null);
  const [bootError, setBootError] = useState('');
  const [mobile, setMobile] = useState(false);
  const [prompt, setPrompt] = useState('');
  const workspace = useWorkspaceData(!!auth?.authenticated);
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
      else if (authRoutes.includes(page)) go('today');
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
    document.title = `${navItems.find((n) => n[0] === page)?.[1] || 'Your workspace'} · Personal Agent`;
  }, [page]);
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
  if (!auth)
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <section className="card max-w-md p-8 text-center">
          <h1 className="text-xl font-semibold">
            {bootError ? 'Your backend could not be reached.' : 'Opening your workspace…'}
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-500">
            {bootError || 'Checking your session.'}
          </p>
          {bootError && (
            <>
              <p className="mt-3 text-xs leading-6 text-slate-500">
                Start personal-agent dashboard from backend/. For frontend development, keep the
                backend on port 8000.
              </p>
              <button className="primary mt-5" onClick={bootstrap}>
                Try again
              </button>
            </>
          )}
        </section>
      </div>
    );
  if (!auth.authenticated)
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
            go('today');
          }}
        />
        <Toast message={message} onDismiss={dismiss} />
      </>
    );
  return (
    <>
      <DashboardLayout
        mobile={mobile}
        setMobile={setMobile}
        name={name}
        page={page}
        go={go}
        notify={notify}
        logout={logout}
        status={workspace.status}
        approvalCount={workspace.approvals.filter((a) => a.actionable).length}
      >
        {workspace.status?.model_setup?.model !== workspace.status?.model &&
          workspace.status?.model_setup?.status === 'ready_restart_required' && (
            <div
              role="status"
              className="mb-6 rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-700"
            >
              The faster model is ready. Restart the dashboard to use{' '}
              {workspace.status.model_setup.model}.
            </div>
          )}
        {workspace.status?.model_setup?.status === 'waiting_for_download' && (
          <div
            role="status"
            className="mb-6 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600"
          >
            The smaller model setup is waiting for its download. You can keep chatting with the
            current model.
          </div>
        )}
        {workspace.error && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
          >
            Could not refresh workspace: {workspace.error}{' '}
            <button onClick={workspace.refresh} className="ml-2 underline">
              Retry
            </button>
          </div>
        )}
        {page === 'today' && (
          <HomePage
            name={name}
            prompt={prompt}
            setPrompt={setPrompt}
            ask={ask}
            busy={chat.busy}
            send={send}
            go={go}
            status={workspace.status}
            tasks={workspace.tasks}
          />
        )}
        {page === 'agent' && (
          <ChatPage
            chat={chat.messages}
            prompt={prompt}
            setPrompt={setPrompt}
            ask={ask}
            busy={chat.busy}
            conversations={workspace.conversations}
            loadConversation={openConversation}
            newConversation={chat.newConversation}
            sessionId={chat.sessionId}
            approvals={workspace.approvals}
            decide={decide}
          />
        )}
        {page === 'telegram' && (
          <TelegramPage
            telegram={workspace.status?.telegram}
            events={workspace.telegramActivity}
            refresh={workspace.refresh}
            notify={notify}
            openConversation={openConversation}
          />
        )}
        {page === 'tasks' && (
          <TasksPage
            tasks={workspace.tasks}
            approvals={workspace.approvals}
            refresh={workspace.refresh}
            notify={notify}
            decide={decide}
          />
        )}
        {page === 'studio' && <ContentStudioPage go={go} />}
        {page === 'connections' && (
          <ConnectionsPage go={go} telegram={workspace.status?.telegram} />
        )}
        {page === 'activity' && (
          <ActivityPage events={workspace.activity} refresh={workspace.refresh} notify={notify} />
        )}
        {authRoutes.includes(page) && (
          <HomePage
            name={name}
            prompt={prompt}
            setPrompt={setPrompt}
            ask={ask}
            busy={chat.busy}
            send={send}
            go={go}
            status={workspace.status}
            tasks={workspace.tasks}
          />
        )}
      </DashboardLayout>
      <Toast message={message} onDismiss={dismiss} />
    </>
  );
}
