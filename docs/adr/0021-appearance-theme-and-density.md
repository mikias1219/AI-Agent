# ADR 0021 — Appearance theme and density

## Status

Accepted (mockup UI v2)

## Context

The updated mockup board requires light and dark palettes with the same semantic
token roles, plus Comfortable / Compact density for list rows and Today. Theme
should follow System when chosen. Preferences must not invent product data.

## Decision

- Persist theme preference in `localStorage` key `aura-theme` (`light` | `dark` |
  `system`) via `ThemeProvider`; resolve System with `prefers-color-scheme` and
  set `data-theme` on `<html>`.
- Persist density in `aura-density` (`comfortable` | `compact`) via
  `DensityProvider`; set `data-density` and drive `--row-*` CSS variables.
- Settings → Appearance edits both; Today exposes a Comfortable | Compact toggle.
- Dark token map keeps accent for actions only; success / warning / danger stay
  status-only.

## Consequences

- Theme is device-local until a profile JSON sync is added later.
- No museum `/components` routes; atoms stay shared under `components/ui`.
- Pause, quiet hours, and hard ceilings are unchanged by appearance.
