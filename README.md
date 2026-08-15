# Benchmark Radar

做 benchmark 的时候发现新东西太多了，所以我干脆搞了个持续爬虫，每天自动从全网抓新的 benchmark 数据。现在已经从 GitHub、Hugging Face、OpenAlex 等 11 个来源抓了 3000+ 条 benchmark 数据，而且还在持续更新。需要的话可以 Star 这个 repo，一键导出数据，或者每天直接获取最新 benchmark 情报。

I kept running into new benchmarks while doing benchmark research, so I built a crawler that continuously collects benchmark-related signals from across the web.

It now tracks **4,000+ records from 11 sources** and keeps updating every day.

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
