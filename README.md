# Benchmark Radar

I kept running into new benchmarks while doing benchmark research, so I built a crawler that continuously collects benchmark-related signals from across the web.

It now tracks **3,000+ records from 11 sources** and keeps updating every day.

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
