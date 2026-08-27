# Source probe evidence — 2026-08-27

This file records only externally verified facts used in the source-coverage audit.

| Source | Verified endpoint or page | Observation | Decision |
|---|---|---|---|
| Hugging Face Daily Papers | `https://huggingface.co/api/daily_papers?limit=5` | HTTP 200 JSON. Each result included a nested `paper` with arXiv-style `id`, title, original publication date, Daily Papers submission date, upstream summary, authors, upvotes, and sometimes GitHub/project URLs. The public Daily Papers page showed community-submitted current papers such as FrontierChallenge and VGI-BENCH. | Integrate as a secondary discovery source that preserves its arXiv identifier for exact deduplication. |
| Kaggle datasets | `https://www.kaggle.com/api/v1/datasets/list?search=benchmark&sortBy=updated&pageSize=5` | HTTP 200 JSON. Results included public URL/ref, title, last-updated timestamp, creator, tags, license, download/view/vote counts and optional subtitle. The current response included benchmark-labelled dataset releases. | Integrate with narrow benchmark/evaluation/data-quality searches; retain source text and tags only. |
| Hugging Face Spaces | `https://huggingface.co/api/spaces?search=benchmark&sort=lastModified&direction=-1&limit=5&full=true` | HTTP 200 JSON. Results included id, creation and modification timestamps, likes, tags and optional maintainer `cardData.short_description`. Current results included Benchmark Leaderboard Race and a legal AI benchmark explorer. | Extend existing Hugging Face source from datasets to Spaces, using only its upstream short description. |
| Zenodo records | `https://zenodo.org/api/records?q=benchmark%20evaluation&sort=mostrecent&page=1&size=5` | HTTP 200 JSON. Records included DOI URLs, publication and modified dates, title, description, creators, resource type and download/view statistics. Current results included a public evaluation audio dataset and benchmark-related research artifacts. | Integrate with focused query set, using record DOI for stable identity. |
| OpenML | `https://www.openml.org/api/v1/json/data/list/limit/5/sort/date/order/desc` | HTTP 412 because this legacy endpoint rejects `sort`/`order` as filters. Official documentation confirms datasets, tasks, flows, runs and benchmark collections with APIs, but the appropriate production query shape was not independently validated in this pass. | Document as a candidate; do not integrate before validating a stable endpoint and freshness semantics. |
| Papers with Code | `https://paperswithcode.com/api/v1/papers/?page=1&items_per_page=5` | Returned HTTP 302 in the live probe, not a verified stable JSON record response. | Document as a candidate; do not build on an unverified/re-routed API. |

## Public pages consulted

- Hugging Face Daily Papers: https://huggingface.co/papers
- OpenML documentation: https://docs.openml.org/
- OpenML home: https://www.openml.org/

## Existing-source context

The repository already collects arXiv, Hugging Face Hub, generic GitHub search, GitHub Releases, OpenReview, Semantic Scholar, OpenAlex, first-party RSS/Atom feeds, Brave web search and Hacker News. The additional implementation in this change fills the observed gaps for organization-scoped GitHub repositories, community-surfaced papers, Kaggle datasets, Hugging Face benchmark Spaces, and Zenodo DOI artifacts.

No source can guarantee discovery of all benchmark work: private repositories, unindexed pages, embargoed papers, deleted records and sources without public feeds/APIs are structurally unavailable. The project therefore records the verified coverage surface and preserves multiple independent discovery paths instead of claiming exhaustive capture.
