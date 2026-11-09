import { useState } from 'react';
import { api } from '../../../shared/api/client.js';

const SCOPE_HINTS = {
  gmail: 'gmail.readonly + gmail.compose (send needs approval)',
  calendar: 'calendar.readonly + calendar.events (writes need approval)',
  drive: 'drive.readonly (writes need approval)',
};

export default function GoogleChannelPanel({ channel, google, notify, refresh }) {
  const [busy, setBusy] = useState('');
  const connected = !!google?.connected;
  const configured = !!google?.oauth_configured;
  const services = google?.services || {};

  async function connect() {
    setBusy('connect');
    try {
      const result = await api('/google/connect', { method: 'POST' });
      if (result.auth_url) {
        window.open(result.auth_url, '_blank', 'noopener,noreferrer');
        notify('Complete Google sign-in in the new tab, then refresh.');
      } else if (result.local_dev_connected) {
        notify('Google marked connected for local development.');
        await refresh?.();
      } else {
        notify(result.detail || 'Google connect response received.');
        await refresh?.();
      }
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy('');
    }
  }

  async function disconnect() {
    setBusy('disconnect');
    try {
      await api('/google/disconnect', { method: 'POST' });
      notify('Google disconnected.');
      await refresh?.();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
      <h2 className="text-sm font-semibold text-slate-900">Google · {channel.name}</h2>
      <p className="mt-1 text-sm text-slate-500">
        {configured
          ? connected
            ? 'OAuth connected. Read tools can run; writes still need approval.'
            : 'OAuth client is configured. Connect your Google account to enable this channel.'
          : 'Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env (free Google Cloud OAuth client), then restart.'}
      </p>
      <p className="mt-2 text-xs text-slate-400">Scopes for this app: {SCOPE_HINTS[channel.id]}</p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-slate-500">OAuth client</dt>
          <dd className="mt-0.5">{configured ? 'Configured' : 'Missing'}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Account</dt>
          <dd className="mt-0.5">{connected ? google.email || 'Connected' : 'Not connected'}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{channel.name} service</dt>
          <dd className="mt-0.5">
            {connected && services[channel.id] !== false ? 'Ready' : 'Unavailable'}
          </dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        {!connected ? (
          <button
            type="button"
            disabled={!!busy || !configured}
            onClick={connect}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy === 'connect' ? 'Connecting…' : `Connect Google for ${channel.name}`}
          </button>
        ) : (
          <button
            type="button"
            disabled={!!busy}
            onClick={disconnect}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700"
          >
            {busy === 'disconnect' ? 'Disconnecting…' : 'Disconnect Google'}
          </button>
        )}
        <button
          type="button"
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700"
          onClick={() => refresh?.()}
        >
          Refresh status
        </button>
      </div>
    </section>
  );
}
