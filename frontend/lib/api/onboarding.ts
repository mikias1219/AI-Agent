import { api } from "./client";

export type OnboardingItem = {
  id: string;
  label: string;
  done: boolean;
};

export type OnboardingState = {
  wizard_completed: boolean;
  checklist_complete: boolean;
  show_checklist: boolean;
  items: OnboardingItem[];
};

export async function getOnboarding(): Promise<OnboardingState> {
  return api<OnboardingState>("/onboarding");
}

export async function completeWizard(input: {
  name?: string;
  timezone?: string;
}): Promise<OnboardingState> {
  return api<OnboardingState>("/onboarding/wizard", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function skipBriefing(): Promise<OnboardingState> {
  return api<OnboardingState>("/onboarding/skip-briefing", {
    method: "POST",
    body: "{}",
  });
}
