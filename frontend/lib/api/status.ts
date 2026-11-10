import { api } from "./client";
import type { StatusPayload } from "./types";

export type { StatusPayload };

export async function getStatus(): Promise<StatusPayload> {
  return api<StatusPayload>("/status");
}
