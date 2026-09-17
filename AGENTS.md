## User Notes

- Use `uv run` to run any python or `uv run pytest` to test.
- Use `uv add` to add a package. Don't modify `pyproject.toml` or `uv.lock` directly.
- Always use f-strings instead of old python format-strings.

## Project Preferences (Standing Rules)

- Favor simple, maintainable solutions suitable for personal use; avoid over-engineering.
- This repository is intended to be public: never commit secrets, real VINs, or real names.
- Use the vocabulary in `CONTEXT.md` in code, logs and user-facing messages.
- Prefer `loguru` for logging.
- Prefer SQLAlchemy, with DB schema defined in `src/schema.py`.
- Do not use migrations/Alembic; apply schema changes directly in the schema file.
- If schema changes, ask the user to delete the old DB and recreate it. DO NOT CREATE ANY MIGRATION LOGIC, user MUST do it.
- Keep DB design lean; avoid unnecessary columns (for example, `updated_at`) and derive fields when practical.
- Keep dates/times in local context for this project.
- launchd is the source of truth for scheduling; avoid app-level date gating logic.
- Never call `subarulink`'s `update()`. It wakes the vehicle. Only `fetch()` is allowed.
- Tests drive the system through `run_once` in `src/bot.py` and assert only on
  messages sent and state persisted. Do not add seams below it.
- Keep `README.md` short and concise.
