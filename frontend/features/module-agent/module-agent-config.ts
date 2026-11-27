/**
 * The agent inside each module (redesign: no separate Chat destination).
 *
 * One agent, scoped per module: each module names what the agent may look at, offers a few
 * prompts as chips, and wraps the question so the answer follows one shape everywhere:
 * the number and its period first, at most two lines of context, then one next step.
 */

export type ModuleId = "today" | "plan" | "money" | "learn" | "library";

export type ModuleAgentConfig = {
  id: ModuleId;
  /** Shown as the panel title, e.g. "Money agent". */
  name: string;
  /** What the agent knows here; also the scope line sent with every question. */
  scope: string;
  /** Placeholder for the ask box. */
  placeholder: string;
  /** Up to four prompts shown as chips. */
  chips: readonly string[];
  /** Bar text when the page has no insight of its own yet. */
  fallbackInsight: string;
};

export const MODULE_AGENTS: Record<ModuleId, ModuleAgentConfig> = {
  today: {
    id: "today",
    name: "Day agent",
    scope: "today's timeline, tasks, habits, money left and items waiting for approval",
    placeholder: "Ask about your day…",
    chips: ["Plan my day", "What should I do next?", "Wrap up my day"],
    fallbackInsight: "Ask what to do next, or let me plan the rest of your day.",
  },
  plan: {
    id: "plan",
    name: "Plan agent",
    scope: "tasks, habits, goals, projects and the calendar",
    placeholder: "Ask the Plan agent…",
    chips: [
      "Fit my unscheduled tasks into today",
      "Why is my score low?",
      "Break a goal into tasks",
      "Plan tomorrow",
    ],
    fallbackInsight: "I can schedule tasks into free time and break goals into steps.",
  },
  money: {
    id: "money",
    name: "Money agent",
    scope: "accounts, income, payslips, transactions, budgets, bills and savings goals",
    placeholder: "Ask about money, or type “250 taxi”…",
    chips: ["How much is left this month?", "Log an expense", "Which bills are due?"],
    fallbackInsight: "Type an expense like “250 taxi”, or ask how much is left.",
  },
  learn: {
    id: "learn",
    name: "Learn agent",
    scope: "saved words, review history and reading plans",
    placeholder: "Ask the Learn agent…",
    chips: ["Teach me 5 new words", "Quiz me on due words", "How is my retention?"],
    fallbackInsight: "I can teach new words and quiz you on the ones that are due.",
  },
  library: {
    id: "library",
    name: "Notes agent",
    scope: "notes, diary entries and files",
    placeholder: "Ask about your notes…",
    chips: ["Summarize this week's diary", "Find a note", "Draft a note from my ideas"],
    fallbackInsight: "I can find, summarize and draft notes from your library.",
  },
};

export const MAX_QUESTION_CHARS = 4000;

/**
 * Hidden context sent with every question from a module (never shown in the chat): what the
 * agent may use here and the answer shape. `extra` adds page facts, e.g. words already saved.
 */
export function agentContext(module: ModuleId, extra?: string): string {
  const config = MODULE_AGENTS[module];
  return [
    `The user is on the ${config.name.replace(/ agent$/, "")} page and asked the ${config.name}.`,
    `Use only their ${config.scope}.`,
    "Answer with the number and its period first, at most two short lines of context,",
    "then one suggested next step. Never invent figures; say what is missing instead.",
    extra?.trim() ?? "",
  ]
    .filter(Boolean)
    .join("\n")
    .slice(0, 4000);
}

/** The question exactly as typed (trimmed and capped); it is what the chat shows. */
export function cleanQuestion(text: string): string {
  return text.trim().slice(0, MAX_QUESTION_CHARS);
}

/** The bar line: the page's own insight when it has one, otherwise the module's hint. */
export function insightLine(module: ModuleId, insight: string | null | undefined): string {
  const text = (insight ?? "").trim();
  return text || MODULE_AGENTS[module].fallbackInsight;
}

/** The module whose agent sits on this path, or null (Needs you, Settings, Agent…). */
export function moduleForPath(pathname: string): ModuleId | null {
  const first = `/${pathname.split("/")[1] ?? ""}`;
  if (first === "/") return "today";
  if (
    ["/tasks", "/habits", "/goals", "/calendar", "/review", "/projects", "/time"].includes(first)
  ) {
    return "plan";
  }
  if (first === "/money") return "money";
  if (first === "/learn") return "learn";
  if (first === "/library") return "library";
  return null;
}
