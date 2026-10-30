import { api } from '../../../shared/api/client.js';
import { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCheck,
  Eye,
  EyeOff,
  Mail,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import Brand from '../../../shared/components/ui/Brand.jsx';
import AppMark from '../../../shared/components/ui/AppMark.jsx';

export default function AuthenticationPage({
  mode,
  setMode,
  onAuthenticated,
  registered,
  emailRequired,
}) {
  const register = mode === 'register';
  const reset = mode === 'reset';
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setError('');
    setShow(false);
  }, [mode]);
  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const fields = new FormData(form);
    const credentials = {
      password: String(fields.get('password') || ''),
      email: String(fields.get('email') || '').trim(),
    };
    setError('');
    setBusy(true);
    try {
      if (register)
        await api('/register', {
          method: 'POST',
          body: { ...credentials, name: String(fields.get('name') || '').trim() },
        });
      const result = await api('/login', { method: 'POST', body: credentials });
      form.reset();
      onAuthenticated(result.user);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="min-h-screen p-4 sm:p-7">
      <div className="mx-auto grid min-h-[calc(100vh-56px)] max-w-[1440px] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-200/30 lg:grid-cols-[1fr_1.05fr]">
        <aside className="relative hidden flex-col overflow-hidden bg-[#eeecfa] p-12 lg:flex">
          <Brand />
          <div className="absolute -right-32 top-36 size-96 rounded-full border border-white/60" />
          <div className="absolute -right-14 top-52 size-64 rounded-full border border-white/70" />
          <div className="relative my-auto py-14">
            <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-white bg-white/60 px-3 py-1.5 text-xs font-medium text-brand-700">
              <Sparkles size={13} /> A little help. A lot more possibilities.
            </span>
            <h2 className="max-w-md text-5xl font-semibold leading-[1.15] tracking-[-2px] text-[#34304d]">
              Your day, with
              <br />a little more
              <br />
              <span className="text-brand-600">breathing room.</span>
            </h2>
            <p className="mt-6 max-w-sm text-sm leading-7 text-[#827b99]">
              One personal agent for your ideas, your apps, and the things you want to get done.
            </p>
            <div className="mt-10 max-w-sm rotate-[-2deg] rounded-2xl border border-white bg-white/90 p-5 shadow-lg shadow-purple-200/30">
              <div className="flex items-center gap-3">
                <span className="rounded-xl bg-brand-50 p-2 text-brand-600">
                  <WandSparkles size={18} />
                </span>
                <div>
                  <p className="text-xs font-semibold">Your agent, wherever you ask.</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Chat here. Continue in Telegram.
                  </p>
                </div>
              </div>
              <div className="mt-5 space-y-2">
                <div className="h-2 w-4/5 rounded bg-slate-100" />
                <div className="h-2 w-full rounded bg-slate-100" />
                <div className="h-2 w-2/3 rounded bg-slate-100" />
              </div>
              <div className="mt-5 flex items-center justify-between">
                <div className="flex gap-2">
                  <AppMark id="telegram" size="size-7" />
                </div>
                <span className="flex items-center gap-1 text-[10px] text-emerald-600">
                  <CheckCheck size={13} /> One shared workspace
                </span>
              </div>
            </div>
          </div>
          <div className="relative flex items-center gap-2 text-xs text-[#8b839e]">
            <ShieldCheck size={15} /> Your workspace. Your decisions.
          </div>
        </aside>
        <div className="flex flex-col px-6 py-7 sm:px-14 xl:px-24">
          <div className="flex justify-between gap-4 text-xs text-slate-400">
            <span className="lg:hidden">
              <Brand />
            </span>
            <span className="ml-auto rounded-full bg-slate-50 px-3 py-1.5">Local workspace</span>
          </div>
          <div className="mx-auto my-auto w-full max-w-sm py-12">
            <span className="mb-6 inline-flex size-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
              {reset ? <Mail size={23} /> : <Sparkles size={23} />}
            </span>
            <h1 className="text-3xl font-semibold tracking-tight">
              {reset
                ? 'Let’s get you back in.'
                : register
                  ? 'Make space for a better day.'
                  : 'Welcome back.'}
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {reset
                ? 'Recover access using your local workspace configuration.'
                : register
                  ? 'Create your personal workspace and meet your everyday agent.'
                  : 'Your ideas, your apps, and your agent are right here.'}
            </p>
            {reset ? (
              <div className="mt-7 rounded-xl border border-brand-100 bg-brand-50 p-5">
                <p className="font-medium text-brand-700">Local password recovery</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Email recovery is not configured. If you use an environment password, update
                  DASHBOARD_PASSWORD_HASH in backend/.env and restart. For a registered account, use
                  the local recovery command described in the backend guide. No email will be sent.
                </p>
                <button
                  onClick={() => setMode('login')}
                  className="mt-4 text-sm font-semibold text-brand-700"
                >
                  Back to login →
                </button>
              </div>
            ) : register && registered ? (
              <div
                role="status"
                className="mt-7 rounded-xl bg-brand-50 p-5 text-sm leading-7 text-slate-600"
              >
                This personal workspace already has an owner. Log in with the existing account.
                <button className="primary mt-4 w-full" onClick={() => setMode('login')}>
                  Go to login
                </button>
              </div>
            ) : (
              <form className="mt-8 space-y-5" onSubmit={submit}>
                {register && (
                  <div>
                    <label htmlFor="name" className="label">
                      Your name
                    </label>
                    <input
                      className="field"
                      id="name"
                      name="name"
                      autoComplete="name"
                      required
                      maxLength={80}
                      placeholder="What should we call you?"
                    />
                  </div>
                )}
                {(register || emailRequired) && (
                  <div>
                    <label htmlFor="email" className="label">
                      Email address
                    </label>
                    <input
                      className="field"
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      maxLength={254}
                      placeholder="you@example.com"
                    />
                  </div>
                )}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="text-sm font-medium">
                      Password
                    </label>
                    {!register && (
                      <button
                        type="button"
                        onClick={() => setMode('reset')}
                        className="text-xs font-medium text-brand-600"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      className="field pr-12"
                      id="password"
                      name="password"
                      type={show ? 'text' : 'password'}
                      autoComplete={register ? 'new-password' : 'current-password'}
                      required
                      minLength={register ? 8 : 1}
                      maxLength={1024}
                      placeholder={register ? 'Create a password' : 'Enter your password'}
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-3 text-slate-400"
                      aria-label={show ? 'Hide password' : 'Show password'}
                      onClick={() => setShow(!show)}
                    >
                      {show ? <EyeOff size={19} /> : <Eye size={19} />}
                    </button>
                  </div>
                  {register && (
                    <p className="mt-2 text-xs text-slate-500">Use at least 8 characters.</p>
                  )}
                </div>
                {error && (
                  <p role="alert" className="text-sm text-rose-600">
                    {error}
                  </p>
                )}
                <button className="primary w-full" type="submit" disabled={busy}>
                  {busy ? 'Please wait…' : register ? 'Create my workspace' : 'Log in'}
                  <ArrowRight size={16} />
                </button>
                <p className="text-center text-[11px] leading-5 text-slate-500">
                  Your private workspace, right on this computer.
                </p>
              </form>
            )}
            {registered && !register && !reset ? (
              <p className="mt-7 text-center text-xs text-slate-400">
                Your personal workspace is already set up.
              </p>
            ) : (
              <p className="mt-7 text-center text-sm text-slate-500">
                {reset
                  ? 'Remember your password?'
                  : register
                    ? 'Already have a workspace?'
                    : 'New here?'}{' '}
                <button
                  className="font-semibold text-brand-600 hover:underline"
                  onClick={() => setMode(register || reset ? 'login' : 'register')}
                >
                  {register || reset ? 'Log in' : 'Create an account'}
                </button>
              </p>
            )}
          </div>
          <p className="text-center text-[11px] text-slate-400">
            One personal agent. A calmer way to get things done.
          </p>
        </div>
      </div>
    </div>
  );
}
