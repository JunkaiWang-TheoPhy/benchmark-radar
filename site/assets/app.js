const CATEGORY_COLORS = {
  benchmark: "#255ea8",
  evaluation: "#dc633f",
  dataset: "#4c948b",
  data_quality: "#c99327",
};
const FALLBACK_COLORS = ["#756aa8", "#397f9a", "#a4576d", "#70833d"];

const byId = (id) => document.getElementById(id);
const state = {
  data: null,
  view: "today",
  todayDate: "",
  date: "",
  q: "",
  kind: "",
  category: "",
  source: "",
  event: "",
};

function element(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  if (options.className) node.className = options.className;
  if (options.text !== undefined) node.textContent = String(options.text);
  if (options.attrs) {
    Object.entries(options.attrs).forEach(([key, value]) => {
      if (value !== undefined && value !== null) node.setAttribute(key, String(value));
    });
  }
  children.filter(Boolean).forEach((child) => node.append(child));
  return node;
}

function replaceChildren(target, children) {
  target.replaceChildren(...children.filter(Boolean));
}

function formatDate(value, options = { dateStyle: "long" }) {
  if (!value) return "Unknown";
  const withTime = value.length === 10 ? `${value}T00:00:00Z` : value;
  return new Intl.DateTimeFormat("en", { timeZone: "UTC", ...options }).format(
    new Date(withTime),
  );
}

function shorten(value, max = 190) {
  if (!value) return "";
  const normalized = value.trim();
  if (normalized.length <= max) return normalized;
  const candidate = normalized.slice(0, max - 1).trimEnd();
  const lastSpace = candidate.lastIndexOf(" ");
  const cutoff = lastSpace >= Math.floor(max * 0.6)
    ? candidate.slice(0, lastSpace)
    : candidate;
  return `${cutoff.replace(/[,:;.!?-]+$/, "")}…`;
}

function option(value, label, selected = false) {
  return element("option", {
    text: label,
    attrs: { value, ...(selected ? { selected: "" } : {}) },
  });
}

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const requestedView = params.get("view");
  state.view = ["today", "trends", "explorer"].includes(requestedView)
    ? requestedView
    : "today";
  if (state.view === "today") {
    state.todayDate = params.get("date") || "";
  } else {
    state.date = params.get("date") || "";
  }
  state.q = params.get("q") || "";
  state.kind = params.get("kind") || "";
  state.category = params.get("category") || "";
  state.source = params.get("source") || "";
  state.event = params.get("event") || "";
}

function writeUrl() {
  const params = new URLSearchParams();
  if (state.view !== "today") params.set("view", state.view);
  const activeDate = state.view === "today" ? state.todayDate : state.date;
  if (activeDate && (state.view !== "today" || activeDate !== state.data?.latest_date)) {
    params.set("date", activeDate);
  }
  if (state.q) params.set("q", state.q);
  if (state.kind) params.set("kind", state.kind);
  if (state.category) params.set("category", state.category);
  if (state.source) params.set("source", state.source);
  if (state.event) params.set("event", state.event);
  const query = params.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}

function setView(view, update = true) {
  state.view = view;
  document.querySelectorAll(".view").forEach((section) => {
    section.hidden = section.id !== `${view}-view`;
  });
  document.querySelectorAll("[data-view]").forEach((button) => {
    if (button.dataset.view === view) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  });
  if (update) writeUrl();
}

function categoryColor(category, index = 0) {
  return CATEGORY_COLORS[category] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

function dailySnapshot(date = state.todayDate) {
  return (
    state.data.days.find((day) => day.date === date) ||
    state.data.days[state.data.days.length - 1]
  );
}

function scoreBlock(item) {
  const score = Number(item.total_score || 0);
  const width = Math.max(0, Math.min(100, (score / 4) * 100));
  const trackFill = element("span", {});
  const track = element("div", { className: "score-track" }, [trackFill]);
  trackFill.style.width = `${width}%`;
  return element("div", { className: "score" }, [
    element("div", { className: "score-value" }, [
      element("strong", { text: score.toFixed(2) }),
      element("span", { text: "/ 4.00" }),
    ]),
    track,
    element("div", { className: "score-label", text: "Priority score" }),
  ]);
}

function pillBar(item) {
  const pills = [
    ...(item.watchlist
      ? [element("span", { className: "pill pill-watchlist", text: `★ ${item.watchlist}` })]
      : []),
    element("span", { className: "pill pill-source", text: item.source }),
    element("span", { className: "pill pill-event", text: item.event_kind }),
    ...(item.categories || []).map((category) =>
      element("span", { className: "pill", text: category.replaceAll("_", " ") }),
    ),
  ];
  if (!(item.categories || []).length) {
    pills.push(element("span", { className: "pill", text: "uncategorized" }));
  }
  return element("div", { className: "pill-bar" }, pills);
}

function signalCard(item, index) {
  const title = element("a", {
    text: item.title,
    attrs: { href: item.url, target: "_blank", rel: "noopener noreferrer" },
  });
  const body = [pillBar(item), element("h3", {}, [title])];
  // The watchlist note is the one line explaining why this artifact is
  // tracked by name, so it leads ahead of the upstream description.
  if (item.watchlist && item.watchlist_note) {
    body.push(element("p", { className: "signal-tldr", text: item.watchlist_note }));
  }
  // An absent description is reported as absent. Filling the gap with a
  // generated sentence would restate the pills above and tell the reader
  // nothing about the artifact.
  if ((item.summary || "").trim()) {
    body.push(element("p", { text: shorten(item.summary) }));
  } else {
    body.push(
      element("p", {
        className: "signal-nodesc",
        text: "No description published at the source.",
      }),
    );
  }
  // The pill bar already states source and categories, so drop the rationale
  // entries that only restate them.
  const rationale = (item.rationale || [])
    .filter(Boolean)
    .filter((reason) => !/^(Matched|Primary record):/.test(reason));
  if (rationale.length) {
    body.push(
      element("p", {
        className: "signal-why",
        text: `Why surfaced: ${rationale.join("; ")}`,
      }),
    );
  }
  return element("article", { className: "signal-card" }, [
    element("div", { className: "signal-rank", text: String(index + 1).padStart(2, "0") }),
    element("div", {}, body),
    scoreBlock(item),
  ]);
}

function attentionCard(item) {
  const details = element("button", {
    className: "detail-button",
    text: "View signal",
    attrs: { type: "button" },
  });
  details.addEventListener("click", () =>
    openDetails({ ...item, snapshot_date: state.todayDate, observation_kind: "attention" }),
  );
  return element("article", { className: "explorer-card attention-card" }, [
    element("div", {}, [
      element("div", { className: "signal-meta" }, [
        element("span", { className: "attention-badge", text: "attention" }),
        element("span", { text: `${item.source} · ${item.event_kind}` }),
      ]),
      element("h3", {}, [
        element("a", {
          text: item.title,
          attrs: {
            href: item.primary_artifact_url || item.url,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        }),
      ]),
      element("p", {
        text: `${metricLabel(item.metrics?.points, "point")} · ${metricLabel(item.metrics?.comments, "comment")} · ${metricLabel(item.metrics?.submissions ?? 1, "submission")}`,
      }),
    ]),
    details,
  ]);
}

function definition(label, value) {
  return element("div", {}, [
    element("dt", { text: label }),
    element("dd", { text: value }),
  ]);
}

function renderToday() {
  const day = dailySnapshot();
  if (!day) return;
  state.todayDate = day.date;
  byId("today-date").value = day.date;

  byId("today-count").textContent = `${day.evidence_count} records`;
  replaceChildren(
    byId("today-list"),
    day.evidence_items.map((item, index) => signalCard(item, index)),
  );
  byId("today-attention-count").textContent =
    `${day.attention.active_count} active · ${day.attention.new_count} new`;
  replaceChildren(
    byId("today-attention-list"),
    day.attention.observations.length
      ? day.attention.observations.map(attentionCard)
      : [
          element("p", {
            className: "empty-state",
            text: "No persisted attention observations for this snapshot.",
          }),
        ],
  );

  const healthEntries = [
    ...day.ingest_health.map((entry) => ({ ...entry, layer: "Radar ingest" })),
    ...day.producer_health.map((entry) => ({ ...entry, layer: "Producer report" })),
  ];
  replaceChildren(
    byId("health-list"),
    healthEntries.map((entry) => {
      const children = [
        element("span", { className: `health-dot${entry.ok ? " ok" : ""}` }),
        element("span", {
          className: "health-name",
          text: `${entry.source} · ${entry.layer}`,
        }),
        element("span", {
          className: "health-count",
          text: entry.ok
            ? entry.item_count
              ? `${entry.item_count} found`
              : "empty"
            : "failed",
        }),
      ];
      if (entry.error) {
        children.push(element("p", { className: "health-detail", text: entry.error }));
      }
      return element("li", {}, children);
    }),
  );
  writeUrl();
}

function deltaText(value) {
  if (!value) return "no change";
  return value > 0 ? `+${value}` : String(value);
}

function domainCard(category, trend, index) {
  const swatch = element("span", { className: "legend-swatch" });
  swatch.style.setProperty("--swatch", categoryColor(category, index));
  // A null delta means the previous scan used a different report limit, so the
  // two counts are not comparable and no change is claimed.
  const comparable = trend.delta !== null && trend.delta !== undefined;
  const delta = comparable ? Number(trend.delta) : 0;
  const rows = [
    ["vs previous scan", comparable ? deltaText(delta) : "not comparable"],
    [
      "recent daily average",
      trend.baseline === null || trend.baseline === undefined
        ? "not enough history"
        : Number(trend.baseline).toFixed(2),
    ],
    ["cumulative", Number(trend.cumulative || 0).toLocaleString()],
  ];
  if (trend.momentum !== null && trend.momentum !== undefined) {
    const percent = Math.round(Number(trend.momentum) * 100);
    rows.splice(2, 0, ["vs its average", `${percent > 0 ? "+" : ""}${percent}%`]);
  }
  return element(
    "article",
    {
      className: `domain-card${!comparable ? "" : delta > 0 ? " is-up" : delta < 0 ? " is-down" : ""}`,
    },
    [
      element("div", { className: "domain-head" }, [
        swatch,
        element("h3", { text: category.replaceAll("_", " ") }),
      ]),
      element("p", { className: "domain-count", text: String(trend.count ?? 0) }),
      element(
        "dl",
        { className: "domain-stats" },
        rows.flatMap(([label, value]) => [
          element("dt", { text: label }),
          element("dd", { text: value }),
        ]),
      ),
    ],
  );
}

function renderDomainMetrics(day) {
  const grid = byId("domain-grid");
  if (!grid) return;
  const trends = day.category_trends || {};
  const entries = Object.entries(trends).sort(
    (a, b) => (b[1].count || 0) - (a[1].count || 0) || a[0].localeCompare(b[0]),
  );
  byId("domain-date").textContent = formatDate(day.date, { dateStyle: "medium" });
  replaceChildren(
    grid,
    entries.length
      ? entries.map(([category, trend], index) => domainCard(category, trend, index))
      : [
          element("p", {
            className: "empty-state",
            text: "No categorized records in this scan.",
          }),
        ],
  );
}

function renderTrends() {
  const categories = state.data.facets.categories;
  replaceChildren(
    byId("trend-legend"),
    [
      ...categories.map((category, index) => {
        const swatch = element("span", { className: "legend-swatch" });
        swatch.style.setProperty("--swatch", categoryColor(category, index));
        return element("span", { className: "legend-item" }, [
          swatch,
          element("span", { text: `Evidence: ${category.replaceAll("_", " ")}` }),
        ]);
      }),
      (() => {
        const swatch = element("span", { className: "legend-swatch attention-swatch" });
        return element("span", { className: "legend-item" }, [
          swatch,
          element("span", { text: "Attention: active" }),
        ]);
      })(),
    ],
  );
  renderDomainMetrics(state.data.days[state.data.days.length - 1]);
  const dayCount = state.data.days.length;
  const trendMessage = byId("trend-message");
  const trendChart = byId("trend-chart");
  if (dayCount === 1) {
    const only = state.data.days[0];
    trendMessage.textContent =
      `History begins ${formatDate(only.date)}. At least two daily snapshots are required to calculate a trend. ` +
      `Baseline: ${only.evidence_count} evidence records and ${only.attention.active_count} active attention signals.`;
    trendChart.hidden = true;
  } else if (dayCount === 2) {
    trendMessage.textContent =
      "Two snapshots are available. The chart shows the first comparable daily change; broader trend language begins with three snapshots.";
    trendChart.hidden = false;
  } else {
    const latest = state.data.days[dayCount - 1];
    const previous = state.data.days[dayCount - 2];
    // Raising the report limit lifts every count at once. Announcing that as
    // movement would report a collection-policy change as a change in field,
    // so the same gate the domain cards use applies to this sentence.
    const comparable =
      (latest.selection || {}).report_limit === (previous.selection || {}).report_limit;
    if (comparable) {
      const evidenceDelta = latest.evidence_count - previous.evidence_count;
      const attentionDelta = latest.attention.active_count - previous.attention.active_count;
      const direction = (value) => (value > 0 ? `up ${value}` : value < 0 ? `down ${Math.abs(value)}` : "flat");
      const movers = Object.entries(latest.category_trends || {})
        .filter(([, trend]) => trend.delta)
        .sort((a, b) => Math.abs(b[1].delta) - Math.abs(a[1].delta))
        .slice(0, 2)
        .map(([category, trend]) => `${category.replaceAll("_", " ")} ${deltaText(trend.delta)}`);
      trendMessage.textContent =
        `Compared with ${previous.date}, surfaced evidence is ${direction(evidenceDelta)} and active attention is ${direction(attentionDelta)}.` +
        (movers.length ? ` Biggest domain moves: ${movers.join(", ")}.` : "");
    } else {
      trendMessage.textContent =
        `${latest.date} used a different report limit than ${previous.date}, so the two scans ` +
        "are not directly comparable. Counts are shown without a change figure.";
    }
    trendChart.hidden = false;
  }
  const maxTotal = Math.max(
    1,
    ...state.data.days.map((day) =>
      Math.max(
        Object.values(day.category_counts).reduce((sum, count) => sum + count, 0),
        day.attention.active_count,
      ),
    ),
  );
  replaceChildren(
    byId("trend-chart"),
    state.data.days.map((day) => {
      const total = Object.values(day.category_counts).reduce((sum, count) => sum + count, 0);
      const segments = categories.map((category, index) => {
        const segment = element("span", {
          className: "bar-segment",
          attrs: { title: `${category.replaceAll("_", " ")}: ${day.category_counts[category] || 0}` },
        });
        segment.style.height = `${((day.category_counts[category] || 0) / maxTotal) * 260}px`;
        segment.style.setProperty("--bar-color", categoryColor(category, index));
        return segment;
      });
      const attentionBar = element("span", {
        className: "attention-volume",
        attrs: { title: `Active attention: ${day.attention.active_count}` },
      });
      attentionBar.style.height = `${(day.attention.active_count / maxTotal) * 260}px`;
      const button = element("button", {
        className: "day-column",
        attrs: {
          type: "button",
          "aria-label": `${formatDate(day.date)}: ${total} evidence category matches across ${day.evidence_count} evidence records and ${day.attention.active_count} attention signals`,
        },
      }, [
        element("span", { className: "series-bars" }, [
          element("span", { className: "bar-stack" }, segments),
          attentionBar,
        ]),
        element("span", { className: "day-label", text: day.date.slice(5) }),
      ]);
      button.addEventListener("click", () => {
        state.todayDate = day.date;
        setView("today");
        renderToday();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      return button;
    }),
  );
  byId("snapshot-count").textContent = `${state.data.snapshot_count} snapshots`;
  replaceChildren(
    byId("trend-table"),
    [...state.data.days].reverse().map((day) => {
      const link = element("a", { text: day.date, attrs: { href: `?date=${day.date}` } });
      link.addEventListener("click", (event) => {
        event.preventDefault();
        state.todayDate = day.date;
        setView("today");
        renderToday();
      });
      return element("tr", {}, [
        element("td", {}, [link]),
        element("td", {
          text: `${formatDate(day.since, { dateStyle: "short", timeStyle: "short" })} → ${formatDate(day.generated_at, { dateStyle: "short", timeStyle: "short" })}`,
        }),
        element("td", { text: day.evidence_count }),
        element("td", { text: countMapText(day.source_counts) }),
        element("td", {
          text: countMapText(day.category_counts),
        }),
        element("td", { text: countMapText(day.event_kind_counts) }),
        element("td", {
          text: `${day.attention.new_count} new · ${day.attention.active_count} active`,
        }),
        element("td", { text: healthSummary(day.ingest_health) }),
      ]);
    }),
  );
}

function metricLabel(value, singular, plural = `${singular}s`) {
  const count = Number(value || 0);
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`;
}

function countMapText(values) {
  const entries = Object.entries(values || {});
  return entries.length
    ? entries
        .map(([name, count]) => `${name.replaceAll("_", " ")} ${count}`)
        .join(" · ")
    : "none";
}

function healthSummary(entries) {
  // A source that returned nothing still succeeded. Only a failure is not ok,
  // and an empty run is reported alongside rather than counted as a fault.
  const total = entries.length;
  const ok = entries.filter((entry) => entry.ok).length;
  const empty = entries.filter((entry) => entry.ok && entry.item_count === 0).length;
  const base = ok === total ? "all ok" : `${ok}/${total} ok`;
  return empty ? `${base} · ${empty} empty` : base;
}

function allObservations() {
  const evidence = state.data.days.flatMap((day) =>
    day.evidence_items.map((item) => ({
      ...item,
      snapshot_date: day.date,
      observation_kind: "evidence",
    })),
  );
  const attention = state.data.days.flatMap((day) =>
    day.attention.observations.map((item) => ({
      ...item,
      snapshot_date: day.date,
      artifact_urls: item.primary_artifact_url ? [item.primary_artifact_url] : [],
      observation_kind: "attention",
    })),
  );
  return [...evidence, ...attention].sort((a, b) => {
    const dateOrder = String(b.snapshot_date).localeCompare(String(a.snapshot_date));
    return dateOrder || Number(b.total_score || 0) - Number(a.total_score || 0);
  });
}

function populateSelect(target, values, label, selected) {
  replaceChildren(target, [
    option("", `All ${label}`),
    ...values.map((value) => option(value, value.replaceAll("_", " "), value === selected)),
  ]);
}

function syncFilters() {
  const observations = allObservations();
  populateSelect(
    byId("kind-filter"),
    state.data.facets.kinds,
    "kinds",
    state.kind,
  );
  populateSelect(
    byId("date-filter"),
    [...new Set(observations.map((item) => item.snapshot_date))].sort().reverse(),
    "dates",
    state.date,
  );
  populateSelect(
    byId("category-filter"),
    [...new Set(observations.flatMap((item) => item.categories || []))].sort(),
    "categories",
    state.category,
  );
  populateSelect(
    byId("source-filter"),
    [...new Set(observations.map((item) => item.source))].sort(),
    "sources",
    state.source,
  );
  populateSelect(
    byId("event-filter"),
    [...new Set(observations.map((item) => item.event_kind))].sort(),
    "events",
    state.event,
  );
  byId("search-filter").value = state.q;
}

function filteredObservations() {
  const query = state.q.trim().toLowerCase();
  return allObservations().filter((item) => {
    const haystack = `${item.title} ${item.summary} ${item.source}`.toLowerCase();
    return (
      (!state.date || item.snapshot_date === state.date) &&
      (!state.kind || item.observation_kind === state.kind) &&
      (!state.category || (item.categories || []).includes(state.category)) &&
      (!state.source || item.source === state.source) &&
      (!state.event || item.event_kind === state.event) &&
      (!query || haystack.includes(query))
    );
  });
}

function openDetails(item) {
  const isAttention = item.observation_kind === "attention";
  const primaryArtifact = item.primary_artifact_url || item.artifact_urls?.[0];
  const scoreEntries = isAttention
    ? [
        [
          item.source === "Hacker News" ? "HN points" : "Activity points",
          Number(item.metrics?.points || 0).toLocaleString(),
        ],
        ["Comments", Number(item.metrics?.comments || 0).toLocaleString()],
        ["Submissions", Number(item.metrics?.submissions ?? 1).toLocaleString()],
        ["Published", formatDate(item.published_at, { dateStyle: "medium" })],
      ]
    : [
        ["Priority", Number(item.total_score || 0).toFixed(2)],
        ["Evidence", Number(item.evidence_score || 0).toFixed(2)],
        ["Relevance", Number(item.relevance_score || 0).toFixed(2)],
        ["Recency", Number(item.recency_score || 0).toFixed(2)],
      ];
  const rationale = element(
    "ul",
    { className: "rationale-list" },
    (item.rationale || []).map((reason) => element("li", { text: reason })),
  );
  const attentionNotice = isAttention
    ? element("div", { className: "attention-notice" }, [
        element("strong", { text: "Not quality-scored" }),
        element("p", {
          text: "This is a public attention signal. Its activity is shown separately from scientific evidence and priority.",
        }),
      ])
    : null;
  const supporting =
    isAttention && item.supporting_observations?.length
      ? element("section", { className: "supporting-signals" }, [
          element("h3", { text: "Supporting submissions" }),
          element(
            "ul",
            {},
            item.supporting_observations.map((record) =>
              element("li", {}, [
                element("a", {
                  text: `${record.source || item.source} #${record.source_id}`,
                  attrs: {
                    href: record.url,
                    target: "_blank",
                    rel: "noopener noreferrer",
                  },
                }),
                element("span", {
                  text: `${formatDate(record.published_at, { dateStyle: "medium" })} · ${metricLabel(record.metrics?.points, "point")} · ${metricLabel(record.metrics?.comments, "comment")}`,
                }),
              ]),
            ),
          ),
        ])
      : null;
  const links = element("div", { className: "detail-links" }, [
    ...(isAttention && primaryArtifact
      ? [
          element("a", {
            className: "primary-link",
            text: "Open primary artifact ↗",
            attrs: {
              href: primaryArtifact,
              target: "_blank",
              rel: "noopener noreferrer",
            },
          }),
        ]
      : []),
    element("a", {
      className: isAttention ? "secondary-link" : "primary-link",
      text: isAttention ? "Open public discussion ↗" : "Open primary source ↗",
      attrs: { href: item.url, target: "_blank", rel: "noopener noreferrer" },
    }),
  ]);
  replaceChildren(byId("detail-content"), [
    element("p", {
      className: "detail-source",
      text: `${item.source} · ${item.event_kind} · ${item.snapshot_date}`,
    }),
    element("h2", { className: "detail-title", text: item.title, attrs: { id: "detail-title" } }),
    element("p", {
      className: item.summary ? "detail-summary" : "detail-summary signal-nodesc",
      text: item.summary || "No description published at the source.",
    }),
    attentionNotice,
    element(
      "dl",
      { className: "detail-grid" },
      scoreEntries.map(([label, value]) => definition(label, value)),
    ),
    element("h3", { text: "Why surfaced" }),
    rationale,
    supporting,
    isAttention
      ? element("p", {
          className: "discovery-note",
          text:
            `Producer discovered ${formatDate(item.discovered_at, { dateStyle: "medium", timeStyle: "short" })} UTC · ` +
            `Radar first observed ${formatDate(item.observed_at, { dateStyle: "medium", timeStyle: "short" })} UTC`,
        })
      : null,
    links,
  ]);
  byId("detail-dialog").showModal();
}

function explorerCard(item) {
  const isAttention = item.observation_kind === "attention";
  const badge =
    isAttention
      ? element("span", { className: "attention-badge", text: "attention" })
      : null;
  const details = element("button", {
    className: "detail-button",
    text: isAttention ? "View signal" : "View evidence",
    attrs: { type: "button" },
  });
  details.addEventListener("click", () => openDetails(item));
  return element("article", { className: "explorer-card" }, [
    element("div", {}, [
      element("div", { className: "signal-meta" }, [
        badge,
        element("span", {
          text: `${item.snapshot_date} · ${item.source} · ${item.event_kind}`,
        }),
      ]),
      element("h3", {}, [
        element("a", {
          text: item.title,
          attrs: {
            href:
              isAttention && (item.primary_artifact_url || item.artifact_urls?.[0])
                ? item.primary_artifact_url || item.artifact_urls[0]
                : item.url,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        }),
      ]),
      element("p", {
        text: isAttention
          ? `${(item.categories || []).join(" · ") || "uncategorized"} · ${metricLabel(item.metrics?.points, "point")} · ${metricLabel(item.metrics?.comments, "comment")} · ${metricLabel(item.metrics?.submissions || 1, "submission")}`
          : `${(item.categories || []).join(" · ") || "uncategorized"} · ${shorten(item.summary, 140)}`,
      }),
    ]),
    details,
  ]);
}

function renderExplorer() {
  syncFilters();
  const observations = filteredObservations();
  const evidenceCount = observations.filter(
    (item) => item.observation_kind === "evidence",
  ).length;
  const attentionCount = observations.length - evidenceCount;
  byId("explorer-count").textContent =
    `${observations.length} result${observations.length === 1 ? "" : "s"} · ` +
    `${evidenceCount} evidence · ${attentionCount} attention`;
  replaceChildren(
    byId("explorer-list"),
    observations.length
      ? observations.map(explorerCard)
      : [
          element("p", {
            className: "empty-state",
            text: "No observations match these filters. Clear one or more filters to widen the view.",
          }),
        ],
  );
  writeUrl();
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      setView(button.dataset.view);
      if (button.dataset.view === "explorer") renderExplorer();
    });
  });
  byId("today-date").addEventListener("change", (event) => {
    state.todayDate = event.target.value;
    renderToday();
  });
  byId("filters").addEventListener("input", () => {
    state.q = byId("search-filter").value;
    state.kind = byId("kind-filter").value;
    state.date = byId("date-filter").value;
    state.category = byId("category-filter").value;
    state.source = byId("source-filter").value;
    state.event = byId("event-filter").value;
    renderExplorer();
  });
  byId("clear-filters").addEventListener("click", () => {
    state.q = "";
    state.kind = "";
    state.date = "";
    state.category = "";
    state.source = "";
    state.event = "";
    renderExplorer();
  });
  byId("dialog-close").addEventListener("click", () => byId("detail-dialog").close());
  byId("detail-dialog").addEventListener("click", (event) => {
    if (event.target === byId("detail-dialog")) byId("detail-dialog").close();
  });
}

const REPO_SLUG = "ktwu01/benchmark-radar";

function setBadgeCount(id, value) {
  const node = byId(id)?.querySelector("[data-count]");
  if (node) node.textContent = Number(value || 0).toLocaleString();
}

async function renderRepoBadges() {
  // Counts are decoration: the badges link out and stay usable if this fails,
  // so a rate-limited API must never surface as an error state.
  try {
    const response = await fetch(`https://api.github.com/repos/${REPO_SLUG}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!response.ok) return;
    const repo = await response.json();
    setBadgeCount("badge-stars", repo.stargazers_count);
    setBadgeCount("badge-forks", repo.forks_count);
    // open_issues_count includes pull requests, so a badge labelled "Issues"
    // built from it overstates the count and disagrees with the page it links
    // to. Ask search for issues only, and leave the badge blank if that fails
    // rather than showing the inflated number.
    const issues = await fetch(
      `https://api.github.com/search/issues?q=${encodeURIComponent(
        `repo:${REPO_SLUG} is:issue is:open`,
      )}&per_page=1`,
      { headers: { Accept: "application/vnd.github+json" } },
    );
    if (issues.ok) {
      setBadgeCount("badge-issues", (await issues.json()).total_count);
    }
  } catch (error) {
    console.debug("Repository badge counts unavailable", error);
  }
}

async function initialize() {
  readUrl();
  bindEvents();
  // Independent of the data file, so badges still render on an error state.
  renderRepoBadges();
  try {
    const response = await fetch("data/radar.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    if (
      state.data.schema_version !== 2 ||
      !Array.isArray(state.data.days) ||
      !state.data.days.length
    ) {
      throw new Error("No compatible snapshots");
    }
    if (!state.data.facets.dates.includes(state.todayDate)) {
      state.todayDate = state.data.latest_date;
    }
    replaceChildren(
      byId("today-date"),
      [...state.data.facets.dates]
        .reverse()
        .map((date) =>
          option(date, formatDate(date, { dateStyle: "medium" }), date === state.todayDate),
        ),
    );
    renderToday();
    renderTrends();
    renderExplorer();
    setView(state.view, false);
    const latest = dailySnapshot(state.data.latest_date);
    // A source that succeeded with zero records is not down: empty and failed
    // are distinct states everywhere else, so only failures are called out.
    const failed = latest.ingest_health.filter((entry) => !entry.ok).length;
    const empty = latest.ingest_health.filter(
      (entry) => entry.ok && entry.item_count === 0,
    ).length;
    // Report what the reader gets, and mention plumbing only when it broke.
    byId("status-copy").textContent =
      `${formatDate(latest.date, { dateStyle: "medium" })} · ${latest.evidence_count} records` +
      (failed ? ` · ${failed} source${failed === 1 ? "" : "s"} failed` : "");
    byId("feed-status").textContent =
      `${latest.evidence_count} ranked evidence · ${latest.attention.active_count} persisted attention`;
    byId("run-status").querySelector(".status-light").classList.add(
      failed === 0 && empty === 0 ? "ok" : "warning",
    );
    byId("build-meta").textContent = `Updated ${formatDate(state.data.generated_at, {
      dateStyle: "medium",
      timeStyle: "short",
    })} UTC`;
  } catch (error) {
    document.querySelectorAll(".view").forEach((section) => {
      section.hidden = true;
    });
    byId("error-state").hidden = false;
    byId("run-status").textContent = "Validated data unavailable";
    console.error(error);
  }
}

initialize();
