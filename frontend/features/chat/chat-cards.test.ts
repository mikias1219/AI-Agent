import { describe, expect, it } from "vitest";
import {
  cardHasActions,
  cardsFromSteps,
  groupThreads,
  kindFromResultType,
  threadTitle,
} from "./chat-cards-logic";
import type { TrailStep } from "./run-trail";

function step(partial: Partial<TrailStep> & { id: string }): TrailStep {
  return { name: "tool", status: "ok", ...partial };
}

describe("cardsFromSteps", () => {
  it("renders from result_type", () => {
    const cards = cardsFromSteps([
      step({ id: "1", name: "task_create", resultType: "task", resultSummary: "buy milk" }),
      step({
        id: "2",
        name: "google_gmail_create_draft",
        resultType: "email_draft",
        resultSummary: "Draft to Sam",
      }),
      step({
        id: "3",
        name: "mystery_tool",
        resultType: "something_new",
        resultSummary: "fallback",
      }),
    ]);
    expect(cards.map((c) => c.kind)).toEqual(["task", "draft", "receipt"]);
  });

  it.each([
    ["plan", "plan"],
    ["approval", "approval"],
    ["receipt", "receipt"],
    ["email_draft", "draft"],
    ["email_sent", "email_sent"],
    ["calendar_event", "calendar"],
    ["calendar_proposal", "calendar"],
    ["task", "task"],
    ["reminder", "reminder"],
    ["suggestion", "suggestion"],
    ["memory_proposal", "memory_proposal"],
    ["search_results", "search_results"],
  ])("maps result_type %s to %s", (resultType, kind) => {
    expect(kindFromResultType(resultType)).toEqual({ kind, fallback: false });
  });

  it("never inspects the tool name", () => {
    const cards = cardsFromSteps([
      step({ id: "1", name: "plan_propose", resultType: "generic", resultSummary: "x" }),
      step({ id: "2", name: "task_create", resultSummary: "y" }),
    ]);
    expect(cards.map((c) => c.kind)).toEqual(["receipt", "receipt"]);
  });

  it("falls back to a receipt for unknown or missing result_type", () => {
    const [unknown, missing, generic] = cardsFromSteps([
      step({ id: "1", resultType: "brand_new", resultSummary: "did a thing" }),
      step({ id: "2", resultSummary: "did another" }),
      step({ id: "3", resultType: "generic", resultSummary: "plain" }),
    ]);
    expect(unknown).toMatchObject({ kind: "receipt", fallback: true, resultType: "brand_new" });
    expect(missing).toMatchObject({ kind: "receipt", fallback: true });
    expect(generic).toMatchObject({ kind: "receipt" });
    expect(generic.fallback).toBeUndefined();
  });

  it("carries id and plan steps from the structured result", () => {
    const [plan, approval] = cardsFromSteps([
      step({
        id: "1",
        resultType: "plan",
        resultSummary: "Plan the trip",
        resultId: "plan-1",
        resultSteps: ["Book flight", "Book hotel"],
      }),
      step({ id: "2", resultType: "approval", resultSummary: "Send email", resultId: "ap-9" }),
    ]);
    expect(plan).toMatchObject({
      kind: "plan",
      id: "plan-1",
      steps: ["Book flight", "Book hotel"],
    });
    expect(approval).toMatchObject({ kind: "approval", id: "ap-9" });
    expect(cardHasActions(plan)).toBe(true);
    expect(cardHasActions(approval)).toBe(true);
  });

  it("does not offer approval actions without an approval id", () => {
    const [card] = cardsFromSteps([step({ id: "1", resultType: "approval", resultSummary: "x" })]);
    expect(cardHasActions(card)).toBe(false);
  });

  it("skips running and failed steps and invents nothing when empty", () => {
    expect(
      cardsFromSteps([
        step({ id: "1", status: "running", resultType: "task" }),
        step({ id: "2", status: "failed", resultType: "task", resultSummary: "nope" }),
      ]),
    ).toEqual([]);
    expect(cardsFromSteps(undefined)).toEqual([]);
  });

  it("truncates long summaries", () => {
    const [card] = cardsFromSteps([
      step({ id: "1", resultType: "task", resultSummary: "x".repeat(400) }),
    ]);
    expect(card.summary).toHaveLength(160);
  });
});

describe("thread list helpers", () => {
  const now = new Date("2026-11-12T15:00:00");

  it("groups threads into Today and Earlier, newest first order kept", () => {
    const groups = groupThreads(
      [
        { id: "a", created_at: "2026-11-12T09:00:00" },
        { id: "b", created_at: "2026-11-11T09:00:00" },
        { id: "c", created_at: "2026-11-01T09:00:00" },
      ],
      now,
    );
    expect(groups.map((g) => [g.label, g.items.map((i) => i.id)])).toEqual([
      ["Today", ["a"]],
      ["Earlier", ["b", "c"]],
    ]);
  });

  it("omits empty groups", () => {
    expect(groupThreads([], now)).toEqual([]);
    expect(groupThreads([{ id: "a", created_at: "2026-11-01T09:00:00" }], now)).toHaveLength(1);
  });

  it("titles from the first user message, else the start time", () => {
    expect(threadTitle("  Plan   my week ", "2026-11-12T09:00:00", now)).toBe("Plan my week");
    expect(threadTitle("y".repeat(80), "2026-11-12T09:00:00", now)).toHaveLength(48);
    expect(threadTitle(undefined, "2026-11-12T09:00:00", now)).toMatch(/^Chat at /);
    expect(threadTitle(undefined, "2026-11-01T09:00:00", now)).toMatch(/^Chat on /);
    expect(threadTitle(undefined, "garbage", now)).toBe("Conversation");
  });
});
