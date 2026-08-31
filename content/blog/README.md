# Blog authoring

Daily posts are generated from `data/snapshots/`. Human analysis lives here as
`<slug>.md`, with an optional `<slug>.zh.md` translation rendered at the same
canonical URL.

Use this front matter in the English source:

```yaml
---
title: What this analysis shows
title_zh: 这篇分析说明了什么
description: A concrete, one-sentence summary for readers and search results.
description_zh: 面向读者和搜索结果的一句话摘要。
published: 2026-08-31
updated: 2026-08-31
author: Koutian Wu
tags: [AI benchmarks, evaluation]
featured: false
draft: true
sources:
  - title: Primary evidence
    url: https://example.com/evidence
---
```

Write ordinary Markdown below the front matter. Raw HTML is displayed as text,
not executed. Set `draft: false` only after checking every claim and source.
