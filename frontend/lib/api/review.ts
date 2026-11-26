import { api } from "./client";

export type ReviewPeriod = "week" | "month";

export type Review = {
  period: ReviewPeriod;
  from: string;
  to: string;
  tasks: {
    planned: number;
    achieved: number;
    partial: number;
    missed: number;
    skipped: number;
    open: number;
    rate: number | null;
    previous_rate: number | null;
    days: {
      date: string;
      planned: number;
      achieved: number;
      partial: number;
      score: number | null;
    }[];
    missed_tasks: { id: string; title: string; day: string; outcome: string; note: string }[];
  };
  time?: { total_minutes: number; by_project: { project: string; minutes: number }[] };
  habits: { habit: string; done: number; due: number; skipped: number; rate: number | null }[];
  money: {
    income_minor: number;
    spent_minor: number;
    saved_minor: number;
    previous_spent_minor: number;
  };
  highlights: string[];
};

export const getReview = (period: ReviewPeriod) => api<Review>(`/review?period=${period}`);
