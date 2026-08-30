<div align="left">

[English](README.md)

</div>

# Benchmark Radar

<!-- 记录数 badge 由数据驱动：每次采集都会根据语料重新生成，因此它反映的是项目实际收集到的数据量 -->

<p align="center">
  <a href="https://benchmark-radar.org/"><img alt="已收集的 benchmark 记录" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fbenchmark-radar.org%2Fdata%2Frecords-badge.json&amp;style=for-the-badge"></a>
  <a href="https://benchmark-radar.org/data/radar.json"><img alt="下载数据集" src="https://img.shields.io/badge/Dataset-download%20JSON-2f81f7?style=for-the-badge&amp;logo=json&amp;logoColor=white"></a>
  <a href="https://x.com/ktwu01"><img alt="X" src="https://img.shields.io/badge/X-000000?style=for-the-badge&amp;logo=x&amp;logoColor=white"></a>
  <a href="https://www.linkedin.com/in/ktwu01"><img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&amp;logo=linkedin&amp;logoColor=white"></a>
  <a href="https://scholar.google.com/citations?user=s9w1k-cAAAAJ&amp;hl=en"><img alt="Google Scholar" src="https://img.shields.io/badge/Google%20Scholar-4285F4?style=for-the-badge&amp;logo=googlescholar&amp;logoColor=white"></a>
</p>

做 benchmark 研究的时候发现新东西太多了，所以我搞了这个持续爬虫，每天自动从全网抓新的 benchmark 相关信息。它目前每天从 arXiv、GitHub、Hugging Face、OpenAlex、OpenReview、各家实验室官方 feed、Brave Search、Semantic Scholar、Hacker News 等来源采集，并持续更新。你如果需要寻找 related work 或找到适合eval自己的agent 的 bench 或者关注最新的 eval 进展，可以看这里哈哈哈：
github.com/ktwu01/benchmark-radar，每天更新，并支持一键导出数据

**几秒找到一个 benchmark，再看模型成绩如何随时间变化。点击下面的动图，查看
SWE-bench Verified 的 saturation 过程。**

<a href="https://benchmark-radar.org/?view=leaderboard&lfrontier=swe_bench_verified">
  <img src="assets/swe-bench-verified.gif" alt="搜索 SWE-bench Verified 并查看模型成绩随时间变化的动画演示" width="720" />
</a>

## 看看这个 dashboard

**Today：过去 24 小时新出现的东西，全部打分排序，再配一段每日简报，说明发生了
什么变化，并附上它引用的证据。**

<a href="https://benchmark-radar.org/">
  <img src="assets/intro-today-page.gif" alt="Today 页面动画演示：新发现 benchmark 的排序信息流，以及附带证据引用的每日简报" width="720" />
</a>

**Leaderboard：各家模型卡到底最常报告哪些 benchmark，以及每个 benchmark 的成绩
如何一路上涨，直到几乎没有提升空间。**

<a href="https://benchmark-radar.org/?view=leaderboard">
  <img src="assets/intro-leaderboard-page.gif" alt="Leaderboard 页面动画演示：按模型卡采用度排序的 benchmark、成绩随时间变化的图表，以及剩余提升空间卡片" width="720" />
</a>

## 使用方法

- **[打开 dashboard](https://benchmark-radar.org/)** — 每日洞察、趋势、热门 benchmark、模型卡采用排名等
- **[通过 RSS 订阅](https://benchmark-radar.org/feed.xml)** — 每天获取最新的 benchmark 情报
- **[下载完整数据集](https://benchmark-radar.org/data/radar.json)** — 免费、公开、机器可读的 JSON，无需爬虫或联系作者
- **[参与贡献](CONTRIBUTING.md)** — 添加 benchmark、模型卡、信源或修复

如果 Benchmark Radar 帮你节省了研究时间，请 **[给仓库点个 Star](https://github.com/ktwu01/benchmark-radar)**，让更多做评测的人发现它。

## 在本地查询

CLI 会下载并校验 Benchmark Radar 网站使用的完整数据，然后全部在本地查询。正式
package 发布前，可以直接从 GitHub 安装，然后第一次运行：

```bash
python -m pip install 'git+https://github.com/ktwu01/benchmark-radar.git'
benchmark-radar init
benchmark-radar search "long-horizon agent benchmark" --scope all --json
benchmark-radar show opencompass-1248-mmmu --json
benchmark-radar recent --recommended --json
benchmark-radar status --json
```

`init` 会把当前 catalog、详情记录和 Radar snapshots 存到 macOS/Linux 的
`~/.benchmark-radar`，Windows 则是当前用户目录下的 `.benchmark-radar`。可以用
`BENCHMARK_RADAR_HOME` 或 `--data-dir` 更改位置。每次开始新的 benchmark 调研前，
显式更新一次：

```bash
benchmark-radar sync
```

`sync` 先检查随 dashboard 发布的很小 manifest；只有 data version 变化时，才从
GitHub Release 下载完整压缩包，因此 CLI 的大文件流量不会占用 dashboard 的 GitHub
Pages 配额。新数据会经过文件大小、SHA-256、catalog 和 snapshots 完整性校验，成功后
原子切换，并删除旧版本，所以稳定状态只保留最新版本。激活失败时，最后一个验证成功
的版本仍可使用。如果操作
系统暂时锁住待删除目录，sync 会明确返回 `cleanup_pending`，并在下次 sync 时重试物理
清理；查询只会使用新版本。搜索命令本身不会联网或暗中改变数据，并会返回可复现的
`data_version`。未来的 Benchmark Radar Skill 应在每次调研开始时运行一次
`sync --json`，随后调用 `search --json` 和 `show --json`；`--json` 是稳定的机器输出，
不加时则输出适合人阅读的文本。

Agent 可以从本仓库安装这个可选、用途无关的 CLI 使用 Skill：

```bash
npx skills add ktwu01/benchmark-radar --skill benchmark-radar
```

Skill 只根据用户当前请求选择 CLI 命令，不预设结果是用于科研、评测设计、模型选择，
还是其他工作。

`catalog` 搜索标准化 benchmark 目录，`radar` 搜索每日情报历史，`all` 同时搜索
两者，但不会擅自合并它们的身份。当前版本是可复现的关键词/token 检索，不是基于
embedding 的 semantic search。只要共享一个 query token 就可以召回候选，再由
fielded BM25 主分数、受控的名称匹配和短语匹配 boost 排序；加权查询覆盖率只作为
同分候选的次级排序和解释，避免与 BM25 重复计分。局部匹配不会被“所有词必须命中”的
硬门槛删除，而是连同判断证据交给 Agent。每条结果都会说明命中与缺失的 token、加权
覆盖率、匹配字段和各项分数组成。`no_lexical_candidates` 表示当前本地数据版本中没有
记录命中任何 query token。`partial_candidates_only` 表示找到了词法证据，但没有候选覆盖
所有 query token；这些记录仍交给 Agent 检查，却不会伪装成已经找到答案。
`full_matches_found` 只表示至少一条记录实现完整词法覆盖，不代表它自动适用。原始排序
分数只在同一次 query 内有意义，不能跨 query 比较。可以按论文、代码仓库、数据集、
开放程度、模态和来源过滤。

Agent 应分别搜索 `catalog` 与 `radar`。Catalog 是标准化 benchmark 记录；Radar 是近期
证据线索，其中可能只是使用某 benchmark 的论文，并不一定发布了新 benchmark。少量、
简短的 query 变体可以桥接 `robot`/`robotics` 等表达差异，但无法找回本地数据根本没有
收录的 benchmark。搜索结果只是候选，不代表已经适用；应调用 `show` 检查详情，再由
Agent 根据用户的真实条件做最终判断。

可选的本地 HTTP API 与 CLI 复用完全相同的查询服务和 JSON 返回结构：

```bash
benchmark-radar serve --host 127.0.0.1 --port 8765
curl 'http://127.0.0.1:8765/api/v1/search?q=agent%20benchmark&scope=all'
```

只读接口包括 `GET /api/v1/search`、
`GET /api/v1/benchmarks/<key-or-slug>`、`GET /api/v1/recent`、
`GET /api/v1/status` 和 `GET /healthz`。CLI 与 HTTP 查询时只读取 managed data
目录，不会临时访问网络。它目前是本地服务，不是已经部署的公共 Search API。以后可以
再增加 MCP 和 semantic retrieval，而不用复制另一套排序逻辑。

`benchmark-radar normalize-external` 和 `benchmark-radar build-data-release` 是维护者
及 CI 的构建命令。普通用户通过 `sync` 更新，不需要运行 normalizer。

搜索排序变更可以在本地通过版本化的稀疏标注数据集复核：

```bash
python scripts/evaluate_search.py
```

报告包含 Hit@5、MRR@20、Recall@20、导航查询 Hit@1，以及已知 Catalog 缺口的 Top-20
部分候选保留率与完整匹配率。未列出的结果按“尚未标注”处理，而不是负例，因此初版
数据集不会虚报 Precision 或 NDCG。在标签得到更广泛的人工复核前，这套 LLM 辅助评测
不会作为 CI gate。

## 更多

- **评分规则：** [`src/benchmark_radar/rubric.py`](src/benchmark_radar/rubric.py)
- **模型卡采用数据：** [`data/model_cards.yml`](data/model_cards.yml)
- **公开语料 schema：** [`docs/cumulative-corpus.schema.json`](docs/cumulative-corpus.schema.json)
- **引用信息：** [`CITATION.cff`](CITATION.cff)
- **配置：** [`config.yml`](config.yml)
- **开发环境：** `python -m pip install -e '.[dev]' && benchmark-radar normalize-external`
- **支持 / 反馈：** [提交 issue](https://github.com/ktwu01/benchmark-radar/issues)
- **联系：** [@ktwu01](https://github.com/ktwu01)
- **开源协议：** MIT

## 加入微信群

扫码加入微信群，获取每日 benchmark 更新、交流评测相关话题：

<img src="assets/wechat-group-qr.jpg" alt="微信群二维码" width="280" />

## 感谢

前沿模型分数层（包括上方的 SWE-bench Verified 时间线）基于 [LLM Stats](https://llm-stats.com) 采集的 benchmark 数据构建，感谢他们把这些数据公开出来。

## 贡献者

感谢所有让 Benchmark Radar 变得更有用的人。

<a href="https://github.com/ktwu01/benchmark-radar/graphs/contributors">
  <img src="assets/contributors.svg" alt="Benchmark Radar 贡献者" />
</a>

## 引用

如果 Benchmark Radar 对你的研究或评测工作有帮助，欢迎引用：

```bibtex
@misc{wu2026benchmarkradar,
  title        = {Benchmark Radar: A Daily, Evidence-First Radar and Machine-Readable Corpus for AI Benchmarks},
  author       = {Wu, Koutian},
  year         = {2026},
  howpublished = {\url{https://github.com/ktwu01/benchmark-radar}},
  note         = {Daily benchmark radar and open dataset}
}
```

机器可读的引用元数据见 [`CITATION.cff`](CITATION.cff)。

## Star 历史

<a href="https://www.star-history.com/#ktwu01/benchmark-radar&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ktwu01/benchmark-radar/star-history/assets/star-history-dark.svg" />
    <img alt="Benchmark Radar Star 历史图" src="https://raw.githubusercontent.com/ktwu01/benchmark-radar/star-history/assets/star-history.svg" />
  </picture>
</a>
