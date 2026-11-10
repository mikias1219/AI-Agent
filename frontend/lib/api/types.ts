export type User = {
  name: string;
  email: string;
};

export type AuthStatus = {
  authenticated: boolean;
  registered: boolean;
  user: User | null;
  email_required: boolean;
};

export type LoginResponse = {
  authenticated: true;
  user: User;
};

export type RegisterResponse = {
  registered: true;
};

export type ModelSetupPayload = {
  status: string;
  model: string;
  updated_at: string;
  restart_required: boolean;
};

export type TelegramStatusPayload = {
  configured: boolean;
  allowed_chat_ids: number[];
  command: string;
  managed: boolean;
  runtime: string;
  last_seen: string | null;
  username: string | null;
  error_type?: string | null;
};

export type StatusPayload = {
  provider: string;
  model_setup: ModelSetupPayload | null;
  model: string;
  active_runtime: string;
  runtime_reason: string | null;
  hermes_installed: boolean;
  ollama_reachable: boolean;
  telegram: TelegramStatusPayload;
};
