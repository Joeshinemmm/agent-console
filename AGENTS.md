# Repository rules

- Modify files only inside this repository. Never modify the ai-agent repository.
- Consume only public JSONL streams; never import or copy ai-agent internals.
- Keep protocol validation and deterministic state reduction independent of the UI.
- Keep dependencies minimal and core logic testable.
- Never commit secrets, credentials, personal paths, prompts, source payloads, or real event logs.
- Use synthetic fixtures only. Do not persist incoming streams by default.
- Run relevant tests and the full test suite after changes; inspect `git diff` and run `git diff --check`.
- Never force push or change remotes without explicit user approval. Push only when requested.
