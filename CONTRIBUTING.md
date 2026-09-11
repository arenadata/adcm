# Contributing to ADCM

Thanks for your interest in contributing to Arenadata Cluster Manager! This document covers the basics: how to report issues, propose changes, and get a pull request merged.

## Ways to contribute

* **Report a bug** or **propose a feature** by opening a GitHub issue.
* **Submit a pull request** with a fix, improvement, or new feature.
* **Improve documentation** — in this repo or in the [user documentation](https://docs.arenadata.io/adcm/).

## Reporting issues

Before opening a new issue, please search existing issues to avoid duplicates. When filing a bug report, include:

* ADCM version (or commit/branch) you're running.
* Steps to reproduce, expected behavior, and what actually happened.
* Relevant logs, stack traces, or screenshots.

## Project structure

ADCM is a monorepo with a few independently developed components — see the [README](README.md#structure) for the overview:

* [`python/`](python/README.md) — Django backend (API, Ansible plugins, task runner). Start with [`ARCHITECTURE.md`](python/docs/ARCHITECTURE.md) and [`CODESTYLE.md`](python/docs/CODESTYLE.md).
* [`adcm-web/`](adcm-web/app/README.md) — frontend (React, yarn).
* [`go/`](go/README.md) — status/event server.

Each has its own README with setup and local run instructions — read the one for the part you're changing before diving in.

## Development workflow

1. **Branch naming**: name your branch after the related ticket, e.g. `ADCM-1234` or `bugfix/ADCM-1234`. If there's no existing ticket for your change, a short descriptive name is fine.
2. **Base branch**: branch off `develop` and target `develop` in your pull request.
3. **Make your change**, following the code style and architecture conventions for the component you're touching (see links above).
4. **Add or update tests** where it makes sense for the change.
5. **Run the checks** for the component(s) you changed before opening a PR (see below).

## Checks before opening a PR

**Backend (`python/`, `dev/linters`, `conf/adcm/python_scripts`)**

```shell
make pretty      # auto-format and fix lint issues (ruff)
make lint        # ruff, pyright, import-linter, license headers, migration checks
make unittests    # Django test suite (spins up a throwaway Postgres container)
```

Run `make help` for the full list of targets.

New Python files need the Apache-2.0 license header — `make pretty` adds it automatically (checked by `dev/linters/license_checker.py`).

**Frontend (`adcm-web/`)**

```shell
cd adcm-web/app
yarn install
yarn test        # tests
```

The project uses ESLint and Prettier — make sure your editor picks up the repo's configs. See [`adcm-web/app/README.md`](adcm-web/app/README.md) for the full setup, including running the dev server against a local backend.

## Commit messages

Prefix commits with the related ticket ID when there is one, e.g.:

```
ADCM-1234: fix stale concern data after host removal
```

Keep the summary line concise; use the body for context if the change isn't self-explanatory.

## Developer Certificate of Origin (DCO)

All commits must be signed off. By adding a `Signed-off-by` line you certify that you wrote the contribution yourself, or otherwise have the right to submit it under the project's license — see the full text at [developercertificate.org](https://developercertificate.org/).

Sign off a commit with the `-s` flag:

```shell
git commit -s -m "ADCM-1234: fix stale concern data after host removal"
```

This appends a line to the commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

Make sure the name and email match your `git config user.name` / `user.email`. Pull requests containing unsigned commits will not be merged. If you forgot to sign off, you can fix it after the fact:

```shell
git commit --amend -s          # last commit
git rebase --signoff HEAD~N    # last N commits
```

then force-push your branch.

## Submitting a pull request

* Keep PRs focused — one logical change per PR is easier to review and merge.
* Fill in a clear description of what changed and why.
* Make sure `make pretty`, `make lint`, and the relevant test suite pass locally.
* Make sure all commits are signed off (see [DCO](#developer-certificate-of-origin-dco) above).
* **The PR must contain a single commit.** It's fine to push follow-up commits while addressing review feedback; squash everything into one commit (e.g. `git rebase -i`, or `git reset --soft <base> && git commit -s`) before it's merged.
* A [`CODEOWNERS`](CODEOWNERS)-based reviewer will be requested automatically; keep pushing follow-up commits during review, then squash to the single final commit and force-push right before merge.

## License

ADCM is licensed under the [Apache License 2.0](LICENSE). By submitting a contribution, you agree that it will be licensed under the same terms.

## Community

Join our open Telegram channel [@arenadata_cm](https://t.me/arenadata_cm) to ask questions, discuss ideas, and suggest improvements to the product.

## Questions

If something here doesn't cover your case, feel free to open an issue, ask in the [Telegram channel](https://t.me/arenadata_cm), or start a discussion — and check the [user documentation](https://docs.arenadata.io/adcm/) for anything related to using (rather than developing) ADCM.
