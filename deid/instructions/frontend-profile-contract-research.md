# FRONTEND-015R Research: Backend Profile Contract Gap

## Current backend contract

- Commands available to frontend are defined by `BACKEND_COMMANDS` and mirrored in backend handlers.
- Backend config coercion only accepts known keys (`CONFIG_KEYS`) and rejects unknown keys in `UPDATE_CONFIG`.
- There are no backend commands/events for:
  - profile list
  - active profile selection
  - save/load profile snapshots

## Blocking mismatch

- Frontend profile workflows currently rely on local storage keys:
  - `deid:settings-profiles:v1`
  - `deid:active-profile:v1`
- Migrating profiles to backend truth cannot be completed without backend profile lifecycle support.

## Required backend contract decision

Choose one canonical backend strategy:

1. Dedicated profile commands/events (`LIST_PROFILES`, `SAVE_PROFILE`, `LOAD_PROFILE`, `SET_ACTIVE_PROFILE`), or
2. Backend-owned persisted profile fields added to supported config schema with explicit active-profile semantics.

## Frontend implementation readiness

- Frontend can remove local profile authority immediately after one canonical backend strategy is implemented and exposed through typed contract constants.
