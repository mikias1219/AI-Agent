"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Banner } from "@/components/ui/banner";
import { apiErrorMessage } from "@/lib/api/client";
import { startTelegram, stopTelegram, testTelegram, verifyTelegram } from "@/lib/api/telegram";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { resolveTelegramAgentState } from "./agent-state";

export type TelegramControlsProps = {
  status: TelegramStatusPayload;
  onChanged: () => void;
};

export function TelegramControls({ status, onChanged }: TelegramControlsProps) {
  const [busy, setBusy] = useState<"verify" | "start" | "stop" | "test" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const state = resolveTelegramAgentState(status);
  const canControl = status.configured;

  async function run(action: "verify" | "start" | "stop" | "test") {
    setBusy(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "verify") {
        const identity = await verifyTelegram();
        setMessage(
          identity.username
            ? `Verified @${identity.username}`
            : "Verified. Bot identity looks good.",
        );
      } else if (action === "start") {
        await startTelegram();
        setMessage("Start requested. Refresh in a few seconds.");
      } else if (action === "stop") {
        await stopTelegram();
        setMessage("Stop requested.");
      } else {
        const result = await testTelegram();
        setMessage(`Test message sent to chat ${result.chat_id}.`);
      }
      onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  if (!canControl) {
    return (
      <Banner tone="warning">
        Set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS in backend/.env, then restart the API.
      </Banner>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          loading={busy === "verify"}
          onClick={() => void run("verify")}
        >
          Verify bot
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy !== null || state === "listening"}
          loading={busy === "start"}
          onClick={() => void run("start")}
        >
          Start listening
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy !== null || !status.managed}
          loading={busy === "stop"}
          onClick={() => void run("stop")}
        >
          Stop
        </Button>
        <Button
          type="button"
          size="sm"
          disabled={busy !== null || status.allowed_chat_ids.length === 0}
          loading={busy === "test"}
          onClick={() => void run("test")}
        >
          Send test message
        </Button>
      </div>
      {message ? <Banner tone="success">{message}</Banner> : null}
      {error ? (
        <Banner tone="danger" role="alert">
          {error}
        </Banner>
      ) : null}
    </div>
  );
}
