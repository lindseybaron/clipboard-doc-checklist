# Contributing

Thanks for helping improve Clipto.

## Quick start

1. Fork and clone the repo.
2. Create a branch from `main`.
3. Bootstrap local tooling:

```bash
bash scripts/bootstrap.sh
```

4. Run tests:

```bash
python -m unittest discover -s tests -v
```

## Development guidelines

- Keep changes focused and small when possible.
- Add/update tests for behavior changes.
- Avoid committing `config.json` (contains personal/local values).
- Keep README and scripts in sync when changing user-facing commands.

## Pull request checklist

- [ ] Branch is up to date with `main`
- [ ] Local tests pass
- [ ] User-facing docs updated (if needed)
- [ ] No secrets or local config included

## Commit style

Use concise, imperative commit titles that explain intent.
