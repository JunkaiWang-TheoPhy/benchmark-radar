# Benchmark 信息源覆盖深度审计与扩展方案

**审计日期：2026-08-27**
**作者：Manus AI**

## 结论

这次扩展的目标不是用单一关键词搜索冒充“全覆盖”，而是建立一个可维护的多路径发现漏斗。仓库原有的论文、代码、Hub、第一方 RSS、会议和网页搜索层已经具有较好的广度；本次补齐了此前最容易漏掉的五种公开信息：**重点实验室新建仓库、社区正在关注的论文、Kaggle 数据集、Hugging Face 的 benchmark/leaderboard Spaces，以及 Zenodo 中带 DOI 的数据或评测工件**。

> **覆盖边界：** 任何自动化系统都不能保证发现“所有” benchmark 信息。私有仓库、尚未公开的工作、未被任何索引收录的网页、无公开 API/RSS 的站点、删除内容和禁运记录，在技术上都不可可靠获取。本实现承诺的是：对可公开、可索引、可稳定拉取的来源，以可审计、可去重、可控成本的方式持续扩大覆盖，而不是做无法验证的全量承诺。

| 结果 | 数值或状态 | 含义 |
|---|---:|---|
| 重点 GitHub 组织注册表 | **360** 个公开 Organization | 超过“至少 300 个 AI lab / 重点 AI 组织”的要求；每项均保存发现查询、样例仓库、匹配词、分层和复核日期。 |
| 新增独立来源 | **4** 个采集器 | `github_organizations`、`huggingface_papers`、`kaggle_datasets`、`zenodo`。 |
| 扩展既有来源 | **1** 项 | Hugging Face 从 datasets 扩展至 **Spaces**，以覆盖公开排行榜与 benchmark explorer。 |
| 新增回归测试 | **11** 项 | 覆盖组织注册表校验、请求预算、故障隔离、来源字段保真、DOI/arXiv/GitHub 去重标识和 Spaces 描述。 |
| 定向测试 | **80 通过** | 新增/相邻的来源与描述测试全部通过。 |
| 站点与本地化测试 | **116 通过，1 跳过** | 新来源已拥有面向读者的名称与采集方式映射。 |
| 干净副本完整 CI | **983 通过** | 基于最新 `origin/main`，按 CI 顺序生成派生资产后全部通过。 |

## 1. 发现漏斗：已有覆盖与本次补齐

原仓库已接入 arXiv、Hugging Face Hub、通用 GitHub 搜索、GitHub Releases、OpenReview、Semantic Scholar、OpenAlex、第一方 RSS/Atom、Brave Web 与 Hacker News。这些来源覆盖论文、主流代码发布、被追踪项目的 release、会议投稿、学术索引、研究机构公告与网页新闻，但对于“名称不含标准关键词的新实验室仓库”“只出现在数据托管站点的发布”“社区先发现的论文”存在结构性盲区。

| 信息类型 | 现有发现方式 | 本次新增/修改 | 为什么重要 |
|---|---|---|---|
| 预印本、论文、方法说明 | arXiv、OpenReview、Semantic Scholar、OpenAlex | Hugging Face Daily Papers | Daily Papers 带有原始 arXiv ID、作者、正文摘要及社区提交时间。它作为第二发现路径，而非替代 arXiv，可发现未命中当前 arXiv 查询但受到社区关注的评测工作。[1] |
| 代码仓库与实现 | 通用 GitHub 关键词搜索、Releases | 360 个重点组织的新建公开仓库 | 通用搜索依赖仓库名、描述和 README 的措辞；组织级枚举可发现像 RSI-Exam 这类名称或文案未命中查询词的发布。GitHub 官方提供组织公开仓库枚举接口。[2] |
| 数据集与可复现实验材料 | Hugging Face datasets、论文与代码 | Kaggle datasets、Zenodo DOI records | 一部分 benchmark 数据只在 Kaggle 或 Zenodo 发布。Kaggle 返回公开数据集的标题、时间、作者、标签与热度指标；Zenodo 提供 DOI、作者、资源类型、说明和下载/访问指标。[3] [4] |
| 排行榜、交互 explorer | Hugging Face datasets、网页搜索 | Hugging Face Spaces | 公开 leaderboard 常被做成 Space 而不是 Dataset。Hub API 会给出 Space 的创建/修改时间和维护者填写的 `short_description`；当前实测结果包含 benchmark leaderboard/explorer。 [5] |
| 官方产品/研究公告 | 第一方 RSS/Atom、Brave | 保持并建议按准入表扩展 | 对有 feed 的实验室应继续优先第一方 feed；其证据质量通常高于二次索引。 |

## 2. 重点 GitHub 组织注册表

新增文件 `data/priority_github_organizations.yml` 保存了 **360** 个公开 GitHub Organization。候选不是凭记忆人工拼出：先对 GitHub Search API 的 12 个主题面执行两轮采集，主题面包括 AI、ML、LLM、benchmark、evaluation、agent、vision、NLP、reinforcement learning、generative AI 与 multimodal；随后仅保留 `owner.type == Organization`、非 fork 仓库，并按主题交叉命中、benchmark/evaluation/dataset/leaderboard 等直接信号、样例仓库和社区信号进行排序。

每条记录至少含登录名、层级、来源 URL、加入日期、复核日期和完整选择证据。`selection_evidence` 记录查询族、原始主题查询、命中词、排序分数与最多三个样例仓库，因此维护者能够复查“为何在表中”，而不是把组织信誉转化为隐藏的模型评分。

| 层级 | 数量 | 执行含义 |
|---|---:|---|
| `priority` | 43 | 多个高信号主题面交叉命中，或有直接 benchmark/evaluation/dataset 证据。 |
| `standard` | 271 | 与 AI/ML/evaluation 生态有明确公开仓库证据，纳入常规组织扫描。 |
| `probation` | 46 | 有相关发现信号但较弱；仍受同一内容筛选，后续按噪声率复核。 |
| 合计 | **360** | 所有条目由加载器强制执行“至少 300 条、有效层级、登录名合法、大小写去重”的约束。 |

其中 `aiming-lab` 已在注册表中。该组织的证据包含 `MetaClaw` 和 `SimpleMem` 等公开仓库，故组织扫描会独立于通用关键词搜索检查其新建仓库。

### 组织扫描的运行规则

`fetch_github_organizations()` 只列举组织的**新建公开仓库**，并且：

1. 默认每个组织最多一页、30 个仓库，总请求上限为 360；在 GitHub Actions 提供的 token 配额内可控。
2. 仅保留创建时间处于本次 lookback 的仓库；接口按创建时间倒序，读到历史条目即停止当前组织分页。
3. 排除 fork、archived 和 disabled 仓库；一个组织的错误仅写入 source health，不阻断其他组织或整个日报。
4. **组织身份不加分。** 它只提供发现入口；所有条目仍使用同一 taxonomy、低价值抑制、评分和跨来源去重。这避免“知名组织的无关仓库自动进入日报”。
5. 每个条目的 GitHub 仓库 URL 参与精确身份去重，因此与通用 GitHub 搜索、arXiv 论文中的代码链接和 GitHub Release 可以合并，而不会重复推送。

## 3. 新增来源的实现和数据质量规则

| 来源键 | API/数据标识 | 采集范围 | 信息保真与去重策略 | 故障策略 |
|---|---|---|---|---|
| `github_organizations` | GitHub Organization repositories | 注册表内组织的新建公开仓库 | 使用源站 description；URL 作为 GitHub 精确工件键；组织层级仅存作审计元数据。 | 单个组织隔离；全体失败才标记失败。 |
| `huggingface_papers` | Daily Papers，arXiv paper ID | 近窗口内被 Daily Papers 收录的工作 | 保留论文的原始发表日期、摘要、作者、arXiv URL，以及可用 GitHub/project URL；arXiv ID 促成精确合并。 | 可选来源，不替代 required 的 arXiv。 |
| `kaggle_datasets` | Kaggle dataset `ref` | 六个窄查询下的最新公开数据集 | 仅用标题、subtitle、description、标签、作者和公开热度；不生成描述。 | 可选；单来源故障不影响其他来源。 |
| `zenodo` | Zenodo record `recid` + DOI | 六个窄查询下的最新公开 DOI 记录 | 使用源站 metadata、作者、下载/访问与 DOI；DOI 参与跨源精确合并。 | 可选；未来日期仍被统一拒绝并记入健康统计。 |
| `huggingface`（修改） | Hub Dataset / Space ID | datasets + Spaces | Space 仅使用维护者的 `cardData.short_description`；若没有源站文本则摘要为空。 | 保持既有 required 来源行为。 |

> **评分原则：** GitHub Organization、Kaggle Dataset 和 Zenodo 是直接工件来源，获得与 GitHub/Hugging Face 工件相同的证据类别信用；Hugging Face Daily Papers 保持为补充发现线索，不能因社区转发而取代论文或源站工件的证据权重。

## 4. 真实接口与端到端验证

对新增来源执行了真实接口的缩小预算冒烟测试。组织扫描以 3 个组织、最多 3 次请求验证；其他来源各用 1 个查询验证。所有四个新采集器均以 HTTP 成功返回，且没有来源警告。随后将它们一并送入项目的真实去重、taxonomy 和评分流水线。

| 来源 | 小预算端到端原始条目 | 健康状态 | 观察 |
|---|---:|---|---|
| GitHub Organizations | 8 | 正常 | 证明组织注册表可以被加载并独立枚举新仓库。 |
| Hugging Face Papers | 40 | 正常 | 包含 `FrontierChallenge`、`Video-IFBench` 等当前论文条目。 |
| Kaggle Datasets | 20 | 正常 | 返回 benchmark/evaluation 命名的数据集；最后仍由 taxonomy 把关。 |
| Zenodo | 18 | 正常，拒绝 2 条未来日期 | 未来日期防线生效，未让异常时间戳挤占当前日报。 |
| 合计 | 88 | 正常 | 去重后 86，taxonomy 合格 52，说明新来源没有绕过质量门。 |

基于最新 `origin/main` 的干净副本按仓库 CI 顺序执行生成器后，全量 Python 测试结果为 **983 passed**。与改动直接相关的代码风格检查、格式检查、来源测试、描述测试、站点测试和本地化测试均已通过。

## 5. 已识别但暂不启用的来源

“能搜到”不等于“应当立刻进生产”。以下来源具有潜力，但本次不把未经验证或缺乏可靠 freshness 语义的接口接入，以免用不稳定来源降低日报质量。

| 候选 | 价值 | 当前阻碍 | 进入生产的验收条件 |
|---|---|---|---|
| OpenML | 有 datasets、tasks、runs、benchmark collections 和多种 API。[6] | 本次实测的旧数据列表 URL 对 `sort/order` 返回 HTTP 412；尚未验证可稳定按更新时间分页的生产查询。 | 找到官方支持的增量查询；固定分页与时间字段；做 7 天 shadow run，并测量有效率/重复率。 |
| Papers with Code | 历史上连接论文、任务、数据集和 leaderboard。 | 实测旧 API URL 返回 302，未验证可长期使用的 JSON 协议与速率限制。 | 确认可公开、稳定的官方 API 或导出；明确许可、更新时间与重复规则。 |
| 更多 OpenReview venue / workshop | 可覆盖 conference 主会之外的 agent、safety、multimodal workshop。 | venue 名称随年份变化，盲目扩大将消耗请求且噪声很高。 | 维护年度 venue allowlist；先在 shadow mode 对每个 venue 测试 30 天。 |
| 第一方研究实验室 feeds | 最优的公告与 release 证据。 | 很多机构没有稳定 RSS/Atom，网页结构变动大。 | 只纳入有稳定 feed 或官方 JSON 的来源；记录 owner、URL、内容类型、关键词门和健康告警。 |
| 竞赛平台与行业 leaderboard | 能覆盖任务定义、数据与结果发布。 | 登录、反爬、许可、动态网页和缺少增量 API 常见。 | 仅使用平台允许的公开 API/官方 RSS；不要爬取受限或需要登录的页面。 |

## 6. 下一轮运营方法

组织注册表不应无限增长而不复核。建议在每周例行维护中读取每个组织 30 天内的原始候选数、taxonomy 合格数、最终发布数和重复合并率。连续 30 天“原始候选多但合格率低于 2%”的条目从 `priority/standard` 降为 `probation`；连续 90 天零候选的条目仍保留证据但降低扫描优先级；有新公开评测、dataset 或 leaderboard 的组织通过同样的 GitHub 查询证据加入表。

| 指标 | 建议门槛 | 要解决的问题 |
|---|---:|---|
| 新来源 health 成功率 | ≥ 99% / 30 天 | 识别接口失效和限流。 |
| 组织源 taxonomy 合格率 | 先观察，不设硬阈值；低于 2% 触发审查 | 控制大组织的工程仓库噪声。 |
| 新来源与既有来源的精确合并率 | 单独报告 | 合并率高不一定坏；它能验证多个来源对同一工件的交叉发现。 |
| 推荐项人工接受率 | ≥ 60% | 检验 taxonomy/阈值是否应调整。 |
| 漏检回归集召回率 | 100% | 将 RSI-Exam、SWE Refactor 等已知案例固化为回归样本，避免修复后再退化。 |

建议先让新增来源以当前 `required: false` 配置运行 **14 天 shadow period**。期间每日保存 health、候选量、合格量、推荐量、重复量和人工判定。只有在结果稳定且未引入大量低价值条目后，再考虑把其中一个来源提升为 required；组织扫描本身应继续保持“发现层”角色，不应被提升为评分捷径。

## 参考资料

[1]: https://huggingface.co/papers "Hugging Face Daily Papers"
[2]: https://docs.github.com/en/rest/repos/repos#list-organization-repositories "GitHub REST API — List organization repositories"
[3]: https://www.kaggle.com/docs/api "Kaggle API documentation"
[4]: https://developers.zenodo.org/ "Zenodo REST API documentation"
[5]: https://huggingface.co/docs/hub/api "Hugging Face Hub API documentation"
[6]: https://docs.openml.org/ "OpenML documentation"
