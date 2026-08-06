# Launch posts

Drafts for the distribution items in issue #88 (tactics 3, 4, and 8), which are decisions
about timing rather than repository changes. Copy is drafted per platform rather than
written once and cross-posted, because the same text reads as spam on the third platform
that sees it.

Every number here was read from `data/model_cards.yml` on 2026-08-05: 30 documents,
10 organizations, 79 benchmarks. Re-check them against
`benchmark-radar export` before posting, since the registry moves.

Two rules these drafts follow deliberately:

- The caveat travels with the numbers. Every post states that this measures vendor
  reporting convention rather than benchmark quality, and that scores are out of scope.
  The audience most likely to share this is also the audience most able to check the
  denominator.
- No claim that "most benchmarks are not adopted". Every tracked benchmark has at least
  one adopter, so that framing is false here. The honest finding is the
  concentration: 21 of 79 benchmarks appear in five or more documents, while 24 appear in
  exactly one and 25 come from a single organization.

Baseline before any of this ships: 8 stars, 6 forks.

## 1. Hacker News

*Format: title under 80 characters, followed by plain body text.*

**Title:** Show HN: Which benchmarks appear in frontier model cards?

I built Benchmark Radar to answer a narrow question: which AI benchmarks do frontier labs actually report when they release a model?

I manually reviewed 30 model cards, system cards, and technical reports from 10 organizations, recording the benchmarks mentioned in each document. The current leaderboard tracks 79 benchmarks. GPQA Diamond leads with 23 cards from 10 organizations, followed by SWE-bench Verified at 18/8 and LiveCodeBench at 15/7.

The unit is the document, not the result row. If one card reports AIME with several scaffolds or pass@k settings, that still counts as one adoption. I publish card count and organization count separately, with organization count used only as a tiebreak.

Important caveat: this measures vendor reporting convention, not benchmark quality. A saturated or contaminated benchmark may rank highly because reporting it has become conventional. I exclude scores because prompting, tools, reasoning budgets, pass@k, and evaluators make most cross-vendor numbers incomparable. The sample is also small at 30 documents.

The second half is an automated daily radar that collects benchmark, evaluation, dataset, and data-quality work from arXiv, OpenReview, Hugging Face, GitHub, Semantic Scholar, OpenAlex, Brave Search, and Hacker News.

Code: https://github.com/ktwu01/benchmark-radar  
Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard  
Data: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

## 2. Reddit r/MachineLearning

*Format: `[P]` project title convention, with finding-first body.*

**Title:** [P] I checked 30 frontier model reports to see which benchmarks they actually use

Of 79 tracked benchmarks, 21 appear in at least five model cards, while 24 appear in exactly one. GPQA Diamond is the most commonly reported, appearing in 23 documents from all 10 organizations in the sample.

I built an open-source project called Benchmark Radar around this question: which benchmarks do frontier labs actually report when releasing models?

The ranking is hand-curated from 30 model cards, system cards, and technical reports. The counted unit is the document, not the result row. Reporting AIME at pass@1, consensus@64, and with tools in one card still contributes one adoption. The leaderboard publishes `card_count` and `organization_count` side by side rather than merging them.

The sample is small, n=30 documents across 10 organizations, so I would not treat this as a full map of evaluation practice.

More importantly, this measures vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks can rank highly precisely because they remain conventional to report. I deliberately exclude scores because vendors differ in prompting, scaffolding, tool access, reasoning budget, pass@k, and evaluation setup.

There is also an automated daily radar that collects new benchmark, eval, dataset, and data-quality work from eight sources, deduplicates it, classifies it with a published taxonomy, and exposes the ranking components.

Project: https://github.com/ktwu01/benchmark-radar  
Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard  
CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

Feedback on the counting method and missing model documents would be especially useful.

## 3. Reddit r/LocalLLaMA

*Format: practitioner-oriented title and body.*

**Title:** I made a leaderboard of the benchmarks that model releases actually report

When a new model drops, I often want to know whether its benchmark table uses broadly shared evaluations or a mostly vendor-specific set. So I read 30 model cards, system cards, and technical reports from 10 organizations and counted benchmark mentions by document.

The current top entries are GPQA Diamond at 23 cards/10 organizations, SWE-bench Verified at 18/8, LiveCodeBench at 15/7, Humanity's Last Exam at 14/8, and AIME at 14/7.

Each document gets at most one vote per benchmark, regardless of how many prompt settings, scaffolds, or pass@k variants it reports. Card count and organization count stay separate, since six vendors using something tells a different story from one vendor using it six times.

This is a leaderboard of reporting convention, not benchmark quality. A benchmark can rank highly even if it is saturated or contaminated because releases still report it. I also leave scores out because results produced with different tools, prompts, reasoning budgets, and evaluators are usually not comparable. The dataset is only 30 documents, so the result should be read as a small, inspectable sample.

The project also runs a daily radar for new benchmarks, evals, datasets, and data-quality work.

Code: https://github.com/ktwu01/benchmark-radar  
Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard  
JSON: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.json

## 4. X / Twitter

*Format: 6-post thread, each post under 280 characters.*

- [x] Posted

**1/6**

Which benchmarks do frontier labs actually report when they release a model?

I reviewed 30 model cards, system cards, and technical reports from 10 organizations. Benchmark Radar now tracks 79 benchmarks.  
https://koutian.is-a.dev/benchmark-radar/?view=leaderboard

**2/6**

Important caveat: this ranks vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks may rank highly because reporting them is conventional. The sample is also small, n=30 documents.

**3/6**

The top three are:

GPQA Diamond: 23 cards, 10 orgs  
SWE-bench Verified: 18, 8  
LiveCodeBench: 15, 7

Card count and organization count are published separately. They are never merged into one score.

**4/6**

The unit is the document. If one card reports AIME at pass@1, consensus@64, and with tools, it still contributes one adoption. A long appendix cannot outvote another vendor.

**5/6**

I exclude benchmark scores. Vendors vary in prompts, scaffolds, tool access, reasoning budgets, pass@k, and evaluators, so their numbers are usually not comparable. A document-level mention survives those differences.

**6/6**

There is also an automated daily radar for new benchmarks, evals, datasets, and data-quality work, with deduplication and explainable ranking components.

MIT licensed: https://github.com/ktwu01/benchmark-radar  
CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

## 5. LinkedIn

*Format: one professional post with short paragraphs.*

- [x] Posted

Which AI benchmarks have become part of the standard model-release vocabulary?

I have been working on Benchmark Radar, an open-source project built around that question. I manually reviewed 30 model cards, system cards, and technical reports from 10 organizations, then recorded which benchmarks each document reports. The current dataset contains 79 benchmarks.

GPQA Diamond appears in 23 documents from all 10 organizations. SWE-bench Verified appears in 18 documents from 8 organizations, and LiveCodeBench in 15 from 7. At the other end, 24 benchmarks appear in exactly one document, and 25 are reported by only one organization.

The counting rule matters. A document contributes at most one adoption per benchmark, even if it contains many prompt settings, scaffolds, or pass@k variants. The leaderboard publishes card count and organization count separately, since repeated use within one organization is different from adoption across several organizations.

This measures vendor reporting convention, not benchmark quality. A saturated or contaminated benchmark can rank highly precisely because it remains conventional to report. Scores are intentionally excluded because vendors differ in prompts, tools, reasoning budgets, pass@k, and evaluators. The sample is also small, n=30, so this is an inspectable starting point rather than a definitive census.

Benchmark Radar also includes an automated daily feed for new benchmarks, evaluations, datasets, and data-quality work.

Project: https://github.com/ktwu01/benchmark-radar  
Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard  
Citable data: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.md

## 6. Xiaohongshu（小红书）

*格式：一篇中文图文笔记，搭配 5 张数据卡片。*

**标题：30 份模型报告，谁最常出现？**

前沿模型发布时，大家到底在报哪些 benchmark？

我整理了 30 份 model card、system card 和技术报告，覆盖 10 家机构，共记录 79 个 benchmark。出现次数最多的三项是：

1. GPQA Diamond：23 份文档，10 家机构
2. SWE-bench Verified：18 份文档，8 家机构
3. LiveCodeBench：15 份文档，7 家机构

统计单位是文档，不是结果行。同一份报告无论展示多少种 prompt、工具或 pass@k 设置，同一个 benchmark 都只计一次。

这个排名衡量的是厂商的报告惯例，不是 benchmark 质量。已经饱和或可能受到污染的评测，也可能因为大家习惯报告而排得很高。项目不比较跨厂商的模型得分，因为 prompt、工具、推理预算和 evaluator 并不一致。目前样本只有 30 份文档。

完整排行榜和可下载数据放在 Benchmark Radar：
https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
CSV：https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

#人工智能 #大模型 #AI评测 #开源项目 #Benchmark

**配图顺序：**

1. 封面：30 份模型报告里，谁最常出现？
2. 前五名排行榜
3. 统计方法：每份文档每个 benchmark 最多计一次
4. 长尾分布：24 个只出现一次，25 个只被一家机构报告
5. 解读边界与项目链接

## 7. Jike（即刻）

*格式：一条中文动态，数据结论在前，项目链接在后。*

我整理了 30 份前沿模型的 model card、system card 和技术报告，想看看发布模型时大家实际在报哪些 benchmark。

目前记录了 79 个 benchmark。GPQA Diamond 出现在 23 份文档中，覆盖全部 10 家机构；SWE-bench Verified 为 18 份、8 家；LiveCodeBench 为 15 份、7 家。

每份文档对同一个 benchmark 最多计一次，文档数和机构数分开公布。这份数据反映报告惯例，不代表 benchmark 质量，也不比较跨厂商的模型得分。样本目前只有 30 份文档。

项目和数据：https://github.com/ktwu01/benchmark-radar
在线排行榜：https://koutian.is-a.dev/benchmark-radar/?view=leaderboard

如果你熟悉模型评测或 model card，欢迎帮我看看这个计数方法有没有漏洞，或者补充还没有收录的模型文档。

## 8. GitHub Release notes for v0.3.0

*Format: GitHub Release title and Markdown release notes.*

- [x] Published on 2026-08-05

Release: https://github.com/ktwu01/benchmark-radar/releases/tag/v0.3.0
Tag: `v0.3.0`
Commit: `3b5524af003ce4b047036eb851dee66dac4b27b4`

**Title:** Benchmark Radar v0.3.0: Model Card Adoption Rank

This release adds the hand-curated Model Card Adoption Rank, which tracks which benchmarks appear in frontier model cards, system cards, and technical reports.

> **Interpretation caveat:** This measures vendor reporting convention, not benchmark quality. A saturated or contaminated benchmark can rank highly because reporting it is conventional. Scores remain out of scope because prompts, scaffolds, tool access, reasoning budgets, pass@k, and evaluators differ across vendors. The current sample is small, with 30 documents.

### Dataset

- 30 curated documents
- 10 organizations
- 79 benchmarks
- 21 benchmarks appearing in at least five documents
- 24 appearing in exactly one document
- 25 reported by exactly one organization

### Counting method

The unit is the document, not the result row. Multiple results for the same benchmark within one document contribute one adoption.

Two counts are published separately:

- `card_count`, the headline count
- `organization_count`, the tiebreak

This distinction separates broad cross-organization use from repeated reporting within one organization.

### Current top five

1. GPQA Diamond: 23 cards, 10 organizations
2. SWE-bench Verified: 18 cards, 8 organizations
3. LiveCodeBench: 15 cards, 7 organizations
4. Humanity's Last Exam: 14 cards, 8 organizations
5. AIME: 14 cards, 7 organizations

### Data artifacts

- [JSON](https://koutian.is-a.dev/benchmark-radar/data/leaderboard.json)
- [CSV](https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv)
- [Markdown](https://koutian.is-a.dev/benchmark-radar/data/leaderboard.md)
- [Shields badge endpoint](https://koutian.is-a.dev/benchmark-radar/data/leaderboard-badge.json)

The automated daily radar remains available alongside the curated leaderboard.

## 9. Cold outreach email

*Format: short individual email with explicit personalization slots.*

**Subject:** A small dataset on how model cards report [BENCHMARK]

Hi [NAME],

I was reading your [BENCHMARK / MODEL CARD / TECHNICAL REPORT] while building a small dataset on which evaluations appear in frontier model releases. I thought you might find the resulting adoption view useful, particularly the entry for [SPECIFIC BENCHMARK OR DETAIL RELEVANT TO THIS PERSON].

Benchmark Radar currently covers 30 documents from 10 organizations and tracks 79 benchmarks. It counts each document once per benchmark, then reports document count and organization count separately.

A necessary caveat: this measures vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks may still rank highly because they are conventional to report. I exclude scores because prompting, scaffolds, tools, reasoning budgets, pass@k, and evaluators differ too much for clean comparison. The n=30 sample is small.

Here is the leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard

If you notice that I represented [BENCHMARK / DOCUMENT] incorrectly, I would appreciate the correction.

Best,  
Koutian Wu  
https://github.com/ktwu01/benchmark-radar

## 10. Zhihu（知乎）

*格式：知乎文章标题与正文，明确说明样本量和统计边界。*

**标题：我统计了 30 份前沿模型报告，看看大家发布模型时到底在报哪些 benchmark**

每次看新模型的技术报告，我都会遇到一个很朴素的问题：哪些 benchmark 已经成了各家都会报的常规项目，哪些主要只在少数机构内部使用？

为此，我整理了 30 份 model card、system card 和技术报告，覆盖 10 家机构，共记录了 79 个 benchmark。现在排在前面的包括：

- GPQA Diamond：23 份文档，10 家机构
- SWE-bench Verified：18 份文档，8 家机构
- LiveCodeBench：15 份文档，7 家机构
- Humanity's Last Exam：14 份文档，8 家机构
- AIME：14 份文档，7 家机构

这里统计的是文档，不是结果行数。同一份报告即使给出了 AIME 的 pass@1、consensus@64 和工具增强结果，也只算一次。否则，一份附录很长的报告就可能抵过另一家机构的采用。

项目同时公布 `card_count` 和 `organization_count`，但不把两者揉成一个总分。六家机构各报一次，和同一家机构连续报六次，含义并不一样。

必须强调，这个排名衡量的是厂商的报告惯例，不是 benchmark 的质量。一个已经饱和或可能受到污染的 benchmark，恰恰可能因为大家习惯继续报告而排得很高。我也没有比较分数，因为不同机构使用的 prompt、scaffold、工具、推理预算、pass@k 和 evaluator 往往不同，同名 benchmark 的两个数字通常不能直接横比。

目前只有 30 份文档，样本很小，不能把它理解成整个评测领域的全景图。更合适的用法，是把它当作一份可核查的采用记录。

数据里也能看到比较明显的长尾：79 个 benchmark 中，21 个至少出现在 5 份文档里，24 个只出现过一次，25 个只被一家机构报告过。所有被收录的 benchmark 都至少有一个采用者。

Benchmark Radar 的另一部分是自动更新的每日雷达，用来收集新的 benchmark、评测、数据集和数据质量工作。

项目地址：https://github.com/ktwu01/benchmark-radar  
排行榜：https://koutian.is-a.dev/benchmark-radar/?view=leaderboard  
CSV：https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

## 11. WeChat（微信公众号）

*格式：微信公众号短文，含标题、正文和数据链接。*

**标题：前沿模型发布时，大家到底在报哪些 Benchmark？**

最近我整理了 30 份 model card、system card 和技术报告，覆盖 10 家机构，想回答一个具体问题：前沿模型发布时，哪些 benchmark 真正出现在报告里？

目前共记录 79 个 benchmark。GPQA Diamond 出现在 23 份文档中，覆盖全部 10 家机构；SWE-bench Verified 为 18 份、8 家；LiveCodeBench 为 15 份、7 家。与此同时，24 个 benchmark 只出现过一次，25 个只被一家机构报告过。

统计单位是文档，而不是结果行。同一份报告里，无论一个 benchmark 有多少种 prompt、scaffold 或 pass@k 设置，都只计一次。项目分别公布文档数和机构数，不合并成一个分数。

需要特别说明：这个榜单衡量的是厂商的报告惯例，不是 benchmark 的质量。已经饱和或受到污染的 benchmark，也可能因为大家习惯报告而排名很高。项目不比较模型得分，因为各家的 prompt、工具、推理预算和 evaluator 不同，数字通常不能直接横比。目前 n=30，样本仍然很小。

Benchmark Radar 还会每日自动收集新的 benchmark、评测、数据集和数据质量工作。

开源地址：https://github.com/ktwu01/benchmark-radar  
排行榜：https://koutian.is-a.dev/benchmark-radar/?view=leaderboard

## 12. Dev.to / Hashnode

*Format: complete Markdown article with exactly three opening paragraphs before the first subheading.*

*Reuse decision: publish this article on DEV first. Paste it verbatim into Hashnode, then set the DEV article URL as the original or canonical URL in Hashnode. Do not reuse the LinkedIn post because it omits the method and data-access detail expected in a technical article.*

**Title:** Which Benchmarks Do Frontier Model Reports Actually Use?

When a lab releases a new model, its evaluation table reflects a mixture of scientific usefulness, historical convention, internal tooling, and what readers expect to see. I built Benchmark Radar to record one observable part of that process: which benchmarks are mentioned in actual model cards, system cards, and technical reports.

The first dataset covers 30 documents from 10 organizations and tracks 79 benchmarks. It is a small sample. GPQA Diamond appears in 23 documents from all 10 organizations, while SWE-bench Verified appears in 18 from 8. The distribution also has a long tail: 24 benchmarks appear in exactly one document, and 25 are reported by only one organization.

This is a measure of vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks can rank highly precisely because reporting them has become conventional. I exclude scores because prompts, scaffolds, tool access, reasoning budgets, pass@k, and evaluators vary across vendors. A document-level mention is the unit that remains comparable across those differences.

### Adoption as an observable reporting choice

A model-release document does not list every evaluation its authors ran. It presents a selected set of results to explain the model to readers. That selection reflects internal tooling, historical practice, the model's intended use, and the comparisons a lab expects readers to recognize.

Benchmark Radar records that visible reporting choice. The source material is the released document itself, not a benchmark website or a third-party leaderboard. Each entry links back to the model card, system card, or technical report that supports it.

The dataset cannot establish that a benchmark is scientifically better, harder, or more predictive than another. It can show which evaluations have become common reporting conventions in the documents sampled.

### Counting documents instead of result rows

The counted unit is the document. A document contributes at most one adoption to a benchmark, even when it reports several prompts, scaffolds, tool settings, or pass@k variants.

This rule prevents a long appendix from receiving more weight than a concise report. A model card with ten AIME result rows and a model card with one AIME result row each contribute one AIME adoption.

### Separating document count from organization count

The leaderboard publishes two values:

- `card_count`: the number of documents that report the benchmark
- `organization_count`: the number of organizations represented by those documents

The values stay separate because repeated reporting within one organization differs from reporting across several organizations. `card_count` determines the headline order, while `organization_count` breaks ties.

### What the first 30 documents show

The current top five are:

1. GPQA Diamond: 23 documents, 10 organizations
2. SWE-bench Verified: 18 documents, 8 organizations
3. LiveCodeBench: 15 documents, 7 organizations
4. Humanity's Last Exam: 14 documents, 8 organizations
5. AIME: 14 documents, 7 organizations

The distribution also has a long tail. Of 79 tracked benchmarks, 21 appear in at least five documents, 24 appear in exactly one document, and 25 are reported by exactly one organization.

The sample contains 30 documents from 10 organizations, so these figures describe the tracked registry rather than the full evaluation field.

### Why the dataset excludes scores

Two results with the same benchmark name may use different prompts, scaffolds, tools, reasoning budgets, pass@k settings, or evaluators. Placing those scores in one cross-vendor table would imply comparability that the source documents do not support.

Benchmark Radar therefore records whether a document reports a benchmark, not which model received the highest number. A saturated or contaminated benchmark can still rank highly because reporting it remains conventional. The ranking measures reporting practice, not benchmark quality.

### The automated daily radar

The project also maintains a daily feed of new work on benchmarks, evaluations, datasets, and data quality. It collects records from arXiv, OpenReview, Hugging Face, GitHub, Semantic Scholar, OpenAlex, Brave Search, and Hacker News, then deduplicates and classifies them with published ranking components.

The daily feed and the hand-curated adoption leaderboard serve different purposes. The feed tracks new work entering the field. The leaderboard tracks benchmarks appearing in model-release documents.

### Using and citing the data

The project is MIT licensed, and the leaderboard is available in several formats:

- Dashboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
- JSON: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.json
- CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv
- Markdown: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.md
- Repository: https://github.com/ktwu01/benchmark-radar

Corrections and additions can be submitted through the repository. The most useful additions are missing model documents and corrections to benchmark mentions already recorded.

## 13. Lobste.rs

*Format: concise title plus one-paragraph authored-by-me comment.*

**Title:** Benchmark Radar: counting benchmark mentions across 30 model reports

**Comment:** I made this to answer which benchmarks frontier labs actually report when releasing models. The hand-curated dataset covers 30 documents from 10 organizations and 79 benchmarks, counting each document at most once per benchmark. It publishes document and organization counts separately. This measures reporting convention, not benchmark quality. Saturated or contaminated benchmarks may rank highly because they remain conventional, and scores are excluded because evaluation setups differ. The sample is small at n=30. The repository is MIT licensed: https://github.com/ktwu01/benchmark-radar

## 14. Product Hunt

*Format: required tagline under 60 characters, followed by a concise description.*

**Tagline:** See which benchmarks appear in 30 frontier model reports

**Description:**

Benchmark Radar tracks which AI benchmarks appear in model cards, system cards, and technical reports. The hand-curated leaderboard covers 30 documents, 10 organizations, and 79 benchmarks, counting each document once per benchmark and publishing document and organization counts separately.

It also runs a daily automated radar for new benchmarks, evals, datasets, and data-quality work.

This measures vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks can rank highly because reporting them is conventional. Scores are excluded because evaluation setups differ, and n=30 is a small sample.

https://koutian.is-a.dev/benchmark-radar/

## 15. Newsletter pitch

*Format: 3-sentence pitch to an AI evaluation newsletter writer.*

I built a small open-source dataset that counts which benchmarks appear across 30 frontier model cards, system cards, and technical reports from 10 organizations. The main finding is concentration plus a long tail: GPQA Diamond appears in 23 documents, while 24 of the 79 tracked benchmarks appear in exactly one. It measures reporting convention, not benchmark quality, so saturated or contaminated benchmarks may rank highly; scores are excluded as evaluation setups differ, and the n=30 sample is explicitly limited: https://github.com/ktwu01/benchmark-radar

## 16. V2EX（分享创造）

*格式：发布到「分享创造」节点，说明项目做了什么、统计边界和希望获得的反馈。*

**标题：[分享创造] Benchmark Radar：统计 30 份模型报告中实际出现的 benchmark**

我做了一个开源项目 Benchmark Radar，其中有一份手工整理的 Model Card Adoption Rank。它回答一个比较具体的问题：前沿模型发布时，各家的 model card、system card 和技术报告实际会报哪些 benchmark？

当前数据包含 30 份文档、10 家机构和 79 个 benchmark。排在前面的是 GPQA Diamond（23 份文档，10 家机构）、SWE-bench Verified（18，8）和 LiveCodeBench（15，7）。

计数时，同一份文档中的同一个 benchmark 最多计一次。项目分开公布文档数和机构数，不将它们合成一个总分。这份排名衡量的是厂商报告惯例，不是 benchmark 质量。模型得分也没有放在一起比，因为各家的 prompt、工具、推理预算和 evaluator 并不一致。当前 30 份文档的样本也还很小。

v0.3.0 已经发布：https://github.com/ktwu01/benchmark-radar/releases/tag/v0.3.0
在线排行榜：https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
CSV：https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv

希望请 V 友帮忙看两件事：统计口径是否合理；还有哪些重要的模型文档没有收录。

## 17. Hugging Face Forums

*Format: dataset announcement with a title, method summary, limitations, and direct data links.*

**Title:** Benchmark Radar: benchmark adoption across 30 frontier model reports

I built Benchmark Radar to track which benchmarks appear in model cards, system cards, and technical reports. The hand-curated dataset currently covers 30 documents from 10 organizations and records 79 benchmarks.

The leading entries are GPQA Diamond at 23 documents from 10 organizations, SWE-bench Verified at 18/8, and LiveCodeBench at 15/7. Each document contributes at most one count per benchmark, regardless of how many prompts, scaffolds, tool settings, or pass@k variants it reports. Document count and organization count are published separately.

This measures vendor reporting convention, not benchmark quality. Saturated or contaminated benchmarks may rank highly because reporting them remains conventional. Scores are excluded because prompts, tools, reasoning budgets, pass@k, and evaluators differ across vendors. The sample is small at 30 documents.

Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv
JSON: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.json
Repository: https://github.com/ktwu01/benchmark-radar

Feedback on the counting method, incorrect entries, and missing model documents would be useful.

## 18. AI community chat messages

*Reuse decision: do not paste the X thread or LinkedIn post into Discord or Slack. The X copy depends on six separate posts, and the LinkedIn copy is too long for a community chat. Use the shorter messages below. The EleutherAI message may be reused verbatim in ML Collective and LAION.*

### 18.1 EleutherAI Discord, ML Collective Discord, and LAION Discord

*Paste this message verbatim in the server channel approved for project or research announcements.*

Hi, I built a small open dataset on which benchmarks frontier labs report when releasing models. Benchmark Radar currently covers 30 model cards, system cards, and technical reports from 10 organizations, with 79 tracked benchmarks.

GPQA Diamond appears in 23 documents from 10 organizations, SWE-bench Verified in 18/8, and LiveCodeBench in 15/7. Each document counts at most once per benchmark, and document count stays separate from organization count.

This measures reporting convention, not benchmark quality. Scores are excluded because evaluation setups differ, and the sample is still small at n=30. I would appreciate feedback on the counting method or model documents I missed.

Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
Repository: https://github.com/ktwu01/benchmark-radar

### 18.2 Hugging Face Discord

*Paste this message verbatim in the server channel approved for community projects. Do not reuse the full LinkedIn post.*

Hi, I published a small open dataset that counts benchmark mentions across 30 frontier model cards, system cards, and technical reports from 10 organizations. It tracks 79 benchmarks and publishes both document count and organization count.

The top three are GPQA Diamond at 23 documents/10 organizations, SWE-bench Verified at 18/8, and LiveCodeBench at 15/7. This measures reporting convention, not benchmark quality. Scores are excluded because evaluation setups differ, and n=30 is a small sample.

CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv
JSON: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.json
Repository: https://github.com/ktwu01/benchmark-radar

Corrections and missing model-report suggestions are welcome.

### 18.3 MLOps Community Slack

*Paste this message verbatim in the workspace channel approved for project announcements. Do not reuse the full LinkedIn post.*

I built Benchmark Radar to make one part of model-release evaluation practice inspectable: which benchmarks vendors include in model cards, system cards, and technical reports.

The current hand-curated dataset covers 30 documents from 10 organizations and 79 benchmarks. Each document counts once per benchmark, with document count and organization count published separately. GPQA Diamond currently leads at 23 documents from 10 organizations.

This is a view of reporting convention, not benchmark quality. Cross-vendor scores are excluded because prompts, tools, reasoning budgets, pass@k, and evaluators differ. The sample is small at n=30.

Leaderboard: https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
CSV: https://koutian.is-a.dev/benchmark-radar/data/leaderboard.csv
Repository: https://github.com/ktwu01/benchmark-radar

Feedback on the data model and counting rule would be useful.

## 19. Substack Note

*Reuse decision: do not paste the full X thread or LinkedIn post. This shorter note is copy-ready.*

I reviewed 30 frontier model cards, system cards, and technical reports from 10 organizations to see which benchmarks they actually report. GPQA Diamond appears in 23 documents, while 24 of the 79 tracked benchmarks appear only once. Benchmark Radar counts each document once per benchmark and publishes document and organization counts separately. This measures reporting convention, not benchmark quality; scores are excluded because evaluation setups differ, and n=30 is a small sample.

https://koutian.is-a.dev/benchmark-radar/?view=leaderboard
