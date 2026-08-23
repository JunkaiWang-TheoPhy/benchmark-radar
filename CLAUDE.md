# Repository Instructions

## Pull request merges

- Do not squash-merge pull requests.
- Merge pull requests with a merge commit so Git preserves branch ancestry and recognizes the branch as merged.

## Before opening a pull request

- Run the full CI sequence locally and get it passing before opening a PR. Do
  not open one against a red local run.
- Run it against a clean checkout (`git worktree add --detach <tmp> <branch>`),
  not your working copy. Generated files such as `site/data/radar.json`,
  `site/data/benchmark-index.json` and `site/data/benchmarks/` are gitignored
  and absent on a fresh CI runner, so a working copy that happens to have them
  on disk passes tests that CI fails.
- The sequence is the one in `.github/workflows/ci.yml`, in order:

      ruff check .
      ruff format --check .
      benchmark-radar normalize-external
      benchmark-radar classify
      pytest -q

- All five must pass. `ruff format --check` runs before everything else, so a
  formatting slip fails the run before a single test executes. Both generators
  run before `pytest` and in that order: `classify` reads the shard directory
  `normalize-external` writes, and the corpus-backed tests skip themselves when
  either artifact is missing.
