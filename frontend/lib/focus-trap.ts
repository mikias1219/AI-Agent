/** Keep Tab / Shift+Tab inside `root` while a dialog or drawer is open. */
export function trapFocus(root: HTMLElement, event: KeyboardEvent): void {
  if (event.key !== "Tab") return;
  const focusable = root.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  );
  if (focusable.length === 0) {
    event.preventDefault();
    return;
  }
  const first = focusable[0]!;
  const last = focusable[focusable.length - 1]!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

const FIELD =
  'input:not([disabled]):not([type="hidden"]), textarea:not([disabled]), select:not([disabled])';
const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Where focus lands when a dialog opens: an element marked `data-autofocus`, else the first
 * field you can type in, else the first button. Starting on a field means you can type at once
 * instead of landing on Close.
 */
export function focusFirst(root: HTMLElement): void {
  const target =
    root.querySelector<HTMLElement>("[data-autofocus]") ??
    root.querySelector<HTMLElement>(FIELD) ??
    root.querySelector<HTMLElement>(FOCUSABLE) ??
    root;
  target.focus();
}
