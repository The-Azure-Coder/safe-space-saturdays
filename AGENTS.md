# Safe Space Saturdays application instructions

## Repository

- URL: `https://github.com/The-Azure-Coder/safe-space-saturdays.git`
- Delivery branch: `mono-repo`
- Commit and push all Safe Space Saturdays source, test, migration, deployment,
  and documentation changes to this repository and branch. Never commit these
  files to the AI Harness repository.

This directory is the complete Safe Space Saturdays application. Keep all product
features, API changes, web and mobile UI, migrations, deployment configuration,
assets, screenshots, and application tests inside this directory.

Run application commands from this directory:

```bash
docker compose up --build
cd web && npm run verify
cd ../api && uv run ruff check . && uv run mypy src && uv run pytest
docker compose config --quiet
graphify update .
```

Do not move application-specific requirements or documentation into the parent AI
harness. Reusable workflow behavior belongs in the parent repository instead.
