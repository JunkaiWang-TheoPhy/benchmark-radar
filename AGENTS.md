# Repository Instructions

## Pull request merges

- Do not squash-merge pull requests.
- Merge pull requests with a merge commit so Git preserves branch ancestry and recognizes the branch as merged.

## Before opening a pull request

- Run the full CI sequence locally and get it passing before opening a PR. Do
  not open one against a red local run.
- Run it against a clean checkout (`git worktree add --detach <tmp> <branch>`),
  not your working copy. Generated files such as `site/data/radar.json` and
  `site/data/radar-bootstrap.json` are gitignored and absent on a fresh CI
  runner, so a working copy that happens to have them on disk passes tests that
  CI fails.
- The sequence is the one in `.github/workflows/ci.yml`, in order:

      ruff check .
      ruff format --check .
      pytest -q
      benchmark-radar classify

- All four must pass. `ruff format --check` runs before the tests, so a
  formatting slip fails the run before a single test executes.
