# Benchmark Radar

<!-- The record-count badge is data-driven: it is regenerated from the corpus on
every collection, so it states what the project actually holds rather than a
hand-edited number (issue #197). -->

[![benchmark records collected](https://img.shields.io/endpoint?url=https%3A%2F%2Fkoutian.is-a.dev%2Fbenchmark-radar%2Fdata%2Frecords-badge.json)](https://koutian.is-a.dev/benchmark-radar/)

I kept running into new benchmarks while doing benchmark research, so I built a
crawler that continuously collects benchmark-related signals from across the
web. It pulls evidence from **arXiv, GitHub, Hugging Face, OpenAlex, OpenReview,
first-party lab feeds, Brave Search, Semantic Scholar, Hacker News, and more**
every day, and keeps updating.

The badge above reads the same corpus the dashboard renders, so the count is the
data, not a claim typed into a README.

**简体中文版本请见 [README.zh-CN.md](README.zh-CN.md).**

## Use it

- **[Open the dashboard](https://koutian.is-a.dev/benchmark-radar/)** — today's insights, trends, popular benchmarks, model-card adoption, and more
- **[Subscribe via RSS](https://koutian.is-a.dev/benchmark-radar/feed.xml)** — get new benchmark signals every day
- **[Download all curated data](https://koutian.is-a.dev/benchmark-radar/data/radar.json)** — export the full machine-readable corpus in one click
- **[Contribute](CONTRIBUTING.md)** — add benchmarks, model cards, sources, or fixes

If this is useful, **star the repo**.

## More

- **Scoring rubric:** [`src/benchmark_radar/rubric.py`](src/benchmark_radar/rubric.py)
- **Model-card adoption data:** [`data/model_cards.yml`](data/model_cards.yml)
- **Public corpus schema:** [`docs/cumulative-corpus.schema.json`](docs/cumulative-corpus.schema.json)
- **Configuration:** [`config.yml`](config.yml)
- **Run locally:** `python -m pip install -e '.[dev]' && benchmark-radar`
- **Support / bugs:** [open an issue](https://github.com/ktwu01/benchmark-radar/issues)
- **Contact:** [@ktwu01](https://github.com/ktwu01)
- **License:** MIT