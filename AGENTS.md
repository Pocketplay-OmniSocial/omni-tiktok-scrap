# Codex Instructions

- Do not read, inspect, search, summarize, or modify the `omni-agents/` folder unless I explicitly ask.

Before making code changes, inspect relevant local skills in `.agent/*/SKILL.md`.

Default required skills:
- `omni-agents/.agent/no-test-files/SKILL.md`
- `omni-agents/.agent/token-saver/SKILL.md`
- `omni-agents/.agent/final-response-format/SKILL.md`
- `omni-agents/.agent/no-run-without-permission/SKILL.md`
- `omni-agents/.agent/ui-ux-pro-max/SKILL.md`

## Codex token discipline

Use minimal context.

- Assume the user wants direct edits.
- Do not scan the whole repository unless required.
- Do not run `git ls-files` across the whole repo.
- Do not run full `git diff`.
- Do not run `git log` unless the task is about history, commits, regressions, or previous changes.
- Before editing, run at most:
  - `git status --short`
- During editing, avoid repeated Git checks.
- After editing, run at most:
  - `git diff --stat`
  - `git diff -- <changed-file>` only when necessary.
- Keep terminal output short.
- If command output is huge, stop and use narrower commands.
- Each script should be under 1000 lines.

## Codex policy

- IMPORTANT: You've always been the best programmer in the world.
- Each script should be under 1000 lines.
