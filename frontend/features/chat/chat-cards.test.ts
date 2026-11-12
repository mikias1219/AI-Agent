import { describe, expect, it } from "vitest";
import { cardsFromSteps } from "./chat-cards-logic";
import type { TrailStep } from "./run-trail";

describe("cardsFromSteps", () => {
  it("renders from result_type", () => {
    const steps: TrailStep[] = [
      {
        id: "1",
        name: "task_create",
        status: "ok",
        resultType: "task",
        resultSummary: "buy milk",
      },
      {
        id: "2",
        name: "google_gmail_create_draft",
        status: "ok",
        resultType: "email_draft",
        resultSummary: "Draft to Sam",
      },
      {
        id: "3",
        name: "mystery_tool",
        status: "ok",
        resultType: "something_new",
        resultSummary: "fallback",
      },
    ];
    const cards = cardsFromSteps(steps);
    expect(cards.map((c) => c.kind)).toEqual(["task", "draft", "generic"]);
  });
});
