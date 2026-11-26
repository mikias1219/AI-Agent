"use client";

import { TimePage } from "@/features/time/time-page";
import { ReviewPage } from "./review-page";

/** Insights: the timer on top, then how the last week or month went. One page, no extra tabs. */
export function InsightsPage() {
  return (
    <div className="flex flex-col gap-6">
      <TimePage embedded />
      <ReviewPage embedded />
    </div>
  );
}
