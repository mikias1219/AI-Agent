/** About 20 seconds per word, never less than a minute. */
export function reviewMinutes(due: number): number {
  return Math.max(1, Math.round((due * 20) / 60));
}
