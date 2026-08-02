const CATEGORY_COLORS = {
  benchmark: "#255ea8",
  evaluation: "#dc633f",
  dataset: "#4c948b",
  data_quality: "#c99327",
  agentic: "#756aa8",
};
const FALLBACK_COLORS = ["#756aa8", "#397f9a", "#a4576d", "#70833d"];

const byId = (id) => document.getElementById(id);
const state = {
  data: null,
  view: "today",
  todayDate: "",
  q: "",
  kind: "",
  category: "",
  source: "",
  organization: "",
  event: "",
  entity: "",
  rubric: "",
  trendReleasedOnly: false,
  // Leaderboard filters carry their own prefixed keys so a shared permalink can
  // hold a Today filter and a Leaderboard filter at once without either view
  // silently reinterpreting the other's `category` or `organization`.
  lq: "",
  ldomain: "",
  lorg: "",
  lera: "",
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

function svgElement(tag, attrs = {}, text = null) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  if (text !== null) node.textContent = String(text);
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

// Expanding a record whose teaser already ran most of the way through the
// description used to re-show that same opening text in full, which reads as
// "this just repeats what I already read" rather than as new information.
// Continuing from where the teaser was cut keeps the expanded view additive.
function summaryRemainder(fullText, teaser) {
  const trimmedFull = (fullText || "").trim();
  const teaserBody = teaser.replace(/…$/, "").trim();
  if (!trimmedFull.startsWith(teaserBody)) return trimmedFull;
  const rest = trimmedFull.slice(teaserBody.length).trim();
  return rest ? `…${rest}` : "";
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
  // Legacy Explorer permalinks resolve to the filterable Today list.
  state.view = ["trends", "map", "leaderboard"].includes(requestedView) ? requestedView : "today";
  state.todayDate = params.get("date") || "";
  state.q = params.get("q") || "";
  state.kind = params.get("kind") || "";
  state.category = params.get("category") || "";
  state.source = params.get("source") || "";
  state.organization = params.get("organization") || "";
  state.event = params.get("event") || "";
  state.entity = params.get("entity") || "";
  state.lq = params.get("lq") || "";
  state.ldomain = params.get("ldomain") || "";
  state.lorg = params.get("lorg") || "";
  state.lera = params.get("lera") || "";
  state.rubric = new URLSearchParams(window.location.hash.slice(1)).get("rubric") || "";
}

function writeUrl() {
  const params = new URLSearchParams();
  if (state.view !== "today") params.set("view", state.view);
  if (state.todayDate && state.todayDate !== state.data?.latest_date) {
    params.set("date", state.todayDate);
  }
  if (state.q) params.set("q", state.q);
  if (state.kind) params.set("kind", state.kind);
  if (state.category) params.set("category", state.category);
  if (state.source) params.set("source", state.source);
  if (state.organization) params.set("organization", state.organization);
  if (state.event) params.set("event", state.event);
  if (state.view === "map" && state.entity) params.set("entity", state.entity);
  if (state.lq) params.set("lq", state.lq);
  if (state.ldomain) params.set("ldomain", state.ldomain);
  if (state.lorg) params.set("lorg", state.lorg);
  if (state.lera) params.set("lera", state.lera);
  const query = params.toString();
  // The rubric dialog is a hashtag, not a query param, so a shared link like
  // #rubric=2 reads as "jump to this section" rather than another filter.
  const hashParams = new URLSearchParams();
  if (state.rubric) hashParams.set("rubric", state.rubric);
  const hash = hashParams.toString();
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}${query ? `?${query}` : ""}${hash ? `#${hash}` : ""}`,
  );
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

function rubricFor(item = null) {
  const version = String(item?.score_version || state.data?.rubric?.scoring_version || 1);
  return state.data?.rubrics?.[version] || state.data?.rubric;
}

function scoreMax(item = null) {
  return Number(item?.score_max || rubricFor(item)?.score_max) || 4;
}

function scoreBlock(item) {
  const score = Number(item.total_score || 0);
  const max = scoreMax(item);
  const width = Math.max(0, Math.min(100, (score / max) * 100));
  const trackFill = element("span", {});
  const track = element("div", { className: "score-track" }, [trackFill]);
  trackFill.style.width = `${width}%`;
  // The label doubles as the way into the rubric. A number presented without
  // a reachable definition of how it was produced asks the reader to trust it
  // on faith, which is the opposite of what an evidence log is for.
  const explain = element("button", {
    className: "score-label score-explain",
    attrs: {
      type: "button",
      "aria-label": `Priority score ${score.toFixed(2)} of ${max.toFixed(2)}. How is this scored?`,
    },
  }, [
    element("span", { text: "Priority score" }),
    element("span", { className: "info-mark", text: "i", attrs: { "aria-hidden": "true" } }),
  ]);
  explain.addEventListener("click", (event) => {
    // The control lives inside a native <summary>; keep rubric access from
    // also toggling the row.
    event.preventDefault();
    event.stopPropagation();
    openRubric(item);
  });
  return element("div", { className: "score" }, [
    element("div", { className: "score-value" }, [
      element("strong", { text: score.toFixed(2) }),
      element("span", { text: `/ ${max.toFixed(2)}` }),
    ]),
    track,
    explain,
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

  syncFilters();
  const observations = filteredObservations();
  const evidenceCount = observations.filter(
    (item) => item.observation_kind === "evidence",
  ).length;
  const attentionCount = observations.length - evidenceCount;
  byId("today-count").textContent =
    `${observations.length} result${observations.length === 1 ? "" : "s"} · ` +
    `${evidenceCount} evidence · ${attentionCount} attention`;
  replaceChildren(
    byId("today-list"),
    observations.length
      ? observations.map(observationCard)
      : [
          element("p", {
            className: "empty-state",
            text: "No observations match these filters. Clear one or more filters to widen the view.",
          }),
        ],
  );

  const healthEntries = [
    ...day.ingest_health.map((entry) => ({ ...entry, layer: "Radar ingest" })),
    ...day.producer_health.map((entry) => ({ ...entry, layer: "Producer report" })),
  ];
  // Fetch plumbing is not what the reader came for, so the roster collapses to
  // one line. It opens itself only when a connector failed, which is the one
  // case where the panel explains a gap in the list beside it.
  const failedCount = healthEntries.filter((entry) => !entry.ok).length;
  byId("health-status").textContent = failedCount
    ? `${failedCount} of ${healthEntries.length} failed`
    : `${healthEntries.length} ok`;
  byId("health-status").classList.toggle("has-failure", failedCount > 0);
  byId("health-panel-details").open = failedCount > 0;
  // Absent on snapshots written before the cap was published, in which case no
  // count can be identified as truncated and all are shown as-is.
  const ingestCap = day.selection?.max_items_per_source ?? null;
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
          // A source that returned exactly the per-source cap was truncated, so
          // the number is a ceiling. "300+ found" says that; "300 found" read as
          // a measured total.
          text: entry.ok
            ? entry.item_count
              ? `${entry.item_count}${entry.item_count === ingestCap ? "+" : ""} found`
              : "empty"
            : "failed",
          ...(entry.item_count === ingestCap
            ? { attrs: { title: `Truncated at the ${ingestCap}-record per-source limit` } }
            : {}),
        }),
      ];
      if (entry.error) {
        children.push(element("p", { className: "health-detail", text: entry.error }));
      }
      return element("li", {}, children);
    }),
  );

  // How many distinct benchmarks/datasets/etc. the whole corpus has ever
  // surfaced, by category (issue #52). `topics` already counts each artifact
  // once across every source and day; this just makes that total legible
  // outside the trend map.
  const topics = state.data.corpus?.aggregates?.topics || [];
  const totalArtifacts = Number(state.data.corpus?.aggregates?.entity_types?.artifact || 0);
  byId("corpus-totals-status").textContent = `${totalArtifacts.toLocaleString()} artifacts`;
  replaceChildren(
    byId("corpus-totals-list"),
    [...topics]
      .sort((a, b) => b.entity_count - a.entity_count)
      .map((topic) =>
        element("li", {}, [
          element("span", {
            className: "health-name",
            text: topic.topic.replace(/_/g, " "),
          }),
          element("span", {
            className: "health-count",
            text: topic.entity_count.toLocaleString(),
          }),
        ]),
      ),
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
  const updatedOnly = Math.max(0, (trend.total_count || 0) - (trend.count || 0));
  if (updatedOnly) {
    rows.push(["also updated (not counted above)", updatedOnly.toLocaleString()]);
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
      element("p", {
        className: "domain-count",
        text: String(trend.count ?? 0),
        attrs: { title: "New releases only. Re-announced updates are tracked separately." },
      }),
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

function sameCollectionContext(a, b) {
  return (
    (a.selection || {}).report_limit === (b.selection || {}).report_limit &&
    JSON.stringify(a.coverage_signature || []) === JSON.stringify(b.coverage_signature || [])
  );
}

function coverageNote(day) {
  return (day.coverage_gaps || []).length
    ? ` Coverage is incomplete: ${day.coverage_gaps.join(", ")} failed.`
    : "";
}

function renderTrends() {
  const categories = state.data.facets.categories;
  byId("trend-released-only").checked = state.trendReleasedOnly;
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
    trendMessage.textContent = sameCollectionContext(
      state.data.days[1],
      state.data.days[0],
    )
      ? "Two snapshots are available. The chart shows the first comparable daily change; broader trend language begins with three snapshots." +
        coverageNote(state.data.days[1])
      : "Two snapshots are available, but their connector coverage or report limit differs, so the change between them is not comparable.";
    trendChart.hidden = false;
  } else {
    const latest = state.data.days[dayCount - 1];
    const previous = state.data.days[dayCount - 2];
    // Raising the report limit lifts every count at once. Announcing that as
    // movement would report a collection-policy change as a change in field,
    // so the same gate the domain cards use applies to this sentence.
    const comparable = sameCollectionContext(latest, previous);
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
        (movers.length ? ` Biggest domain moves: ${movers.join(", ")}.` : "") +
        coverageNote(latest);
    } else {
      trendMessage.textContent =
        `${latest.date} used different connector coverage or a different report limit than ${previous.date}, so the two scans ` +
        "are not directly comparable. Counts are shown without a change figure.";
    }
    trendChart.hidden = false;
  }
  const countsFor = (day) =>
    state.trendReleasedOnly ? day.category_counts_released : day.category_counts;
  const maxTotal = Math.max(
    1,
    ...state.data.days.map((day) =>
      Math.max(
        Object.values(countsFor(day)).reduce((sum, count) => sum + count, 0),
        day.attention.active_count,
      ),
    ),
  );
  replaceChildren(
    byId("trend-chart"),
    state.data.days.map((day, dayIndex) => {
      const dayCounts = countsFor(day);
      const total = Object.values(dayCounts).reduce((sum, count) => sum + count, 0);
      const segments = categories.map((category, index) => {
        const segment = element("span", { className: "bar-segment" });
        segment.style.height = `${((dayCounts[category] || 0) / maxTotal) * 260}px`;
        segment.style.setProperty("--bar-color", categoryColor(category, index));
        return segment;
      });
      const attentionBar = element("span", { className: "attention-volume" });
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
      const previous = state.data.days[dayIndex - 1];
      const show = () => {
        // Escape stays honoured until the pointer or focus leaves and returns,
        // so the card does not spring back while the column is still active.
        if (dismissedTooltipColumn === button) return;
        // Clear the previous column's description first: moving between columns
        // must never leave two triggers pointing at one card.
        hideDayTooltip();
        showDayTooltip(button, day, previous, dayCounts, categories);
      };
      button.showDayTooltip = show;
      button.addEventListener("pointerenter", show);
      button.addEventListener("focus", show);
      // Mixed pointer and keyboard use: leaving with the mouse must not close a
      // card the keyboard still owns, so hand it back to the focused column.
      // An Escape dismissal lifts only once the column is neither hovered nor
      // focused; otherwise taking the mouse off a focused column would undo the
      // dismissal and reopen the card the reader just closed.
      button.addEventListener("pointerleave", releaseDayTooltip);
      button.addEventListener("blur", releaseDayTooltip);
      button.addEventListener("click", () => {
        state.todayDate = day.date;
        setView("today");
        renderToday();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      return button;
    }),
  );
  hideDayTooltip();
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

// The chart exists to compare days, so the tooltip answers only what made this
// column this tall and whether that is up or down. Momentum, baselines, and
// cumulative totals stay on the domain cards rather than being repeated here.
const TOOLTIP_CATEGORY_LIMIT = 4;

// The column whose card is open, so a scroll or resize can re-place it, and the
// column Escape dismissed, so re-entering is required before it opens again.
let openTooltipColumn = null;
let dismissedTooltipColumn = null;

function showDayTooltip(column, day, previous, dayCounts, categories) {
  const tooltip = byId("day-tooltip");
  const total = Object.values(dayCounts).reduce((sum, count) => sum + count, 0);
  // A different report limit or connector set lifts every count at once, so the
  // same gate the headline sentence uses decides whether a delta is meaningful.
  const comparable = previous && sameCollectionContext(day, previous);
  const previousTotal = comparable
    ? Object.values(
        state.trendReleasedOnly
          ? previous.category_counts_released
          : previous.category_counts,
      ).reduce((sum, count) => sum + count, 0)
    : null;
  const ranked = categories
    .map((category, index) => ({
      category,
      count: dayCounts[category] || 0,
      color: categoryColor(category, index),
    }))
    .filter((entry) => entry.count > 0)
    .sort((a, b) => b.count - a.count);
  const shown = ranked.slice(0, TOOLTIP_CATEGORY_LIMIT);
  const restCount = ranked
    .slice(TOOLTIP_CATEGORY_LIMIT)
    .reduce((sum, entry) => sum + entry.count, 0);

  const rows = shown.map((entry) => {
    const swatch = element("span", { className: "legend-swatch" });
    swatch.style.setProperty("--swatch", entry.color);
    return element("span", { className: "day-tooltip-row" }, [
      swatch,
      element("span", {
        className: "day-tooltip-name",
        text: entry.category.replaceAll("_", " "),
      }),
      element("span", { className: "day-tooltip-value", text: entry.count }),
    ]);
  });
  if (restCount) {
    rows.push(
      element("span", { className: "day-tooltip-row day-tooltip-rest" }, [
        element("span", {
          className: "day-tooltip-name",
          text: `+${ranked.length - shown.length} more categories`,
        }),
        element("span", { className: "day-tooltip-value", text: restCount }),
      ]),
    );
  }

  replaceChildren(tooltip, [
    element("span", { className: "day-tooltip-date", text: formatDate(day.date) }),
    element("span", {
      className: "day-tooltip-total",
      text:
        `${metricLabel(total, "category match", "category matches")}` +
        (previousTotal === null
          ? ""
          : total === previousTotal
            ? ` · flat vs ${previous.date.slice(5)}`
            : ` · ${deltaText(total - previousTotal)} vs ${previous.date.slice(5)}`),
    }),
    rows.length ? element("span", { className: "day-tooltip-rows" }, rows) : null,
    element("span", {
      className: "day-tooltip-attention",
      text: `Active attention: ${day.attention.active_count}`,
    }),
  ]);

  tooltip.hidden = false;
  tooltip.setAttribute("aria-hidden", "false");
  // Point the trigger at the card while it is open. Without this the breakdown
  // is visual only: a screen reader on the focused column would never reach it.
  column.setAttribute("aria-describedby", tooltip.id);
  openTooltipColumn = column;
  positionDayTooltip(tooltip, column);
  // Tabbing to an off-screen column scrolls the chart after focus fires, which
  // would leave the card behind. Re-place it once that scrolling has settled.
  requestAnimationFrame(() => {
    if (openTooltipColumn === column && !tooltip.hidden) {
      positionDayTooltip(tooltip, column);
    }
  });
}

function positionDayTooltip(tooltip, column) {
  const frame = tooltip.parentElement;
  // Drop any narrowing a previous cramped placement applied, so every hover is
  // measured at the card's natural width.
  tooltip.style.maxWidth = "";
  const frameBox = frame.getBoundingClientRect();
  const columnBox = column.getBoundingClientRect();
  const width = tooltip.offsetWidth;
  const height = tooltip.offsetHeight;
  // Reads the live width, so a placement that narrows the card first still
  // clamps against its new size rather than the width measured on entry.
  const clampLeft = (value) =>
    Math.min(
      Math.max(value, 8),
      Math.max(frame.clientWidth - tooltip.offsetWidth - 8, 8),
    );
  // The bar stack is a fixed-height plotting box, so its own top says nothing
  // about how tall the rendered bars are. Measure the drawn segments instead.
  const drawn = [...column.querySelectorAll(".bar-segment, .attention-volume")]
    .map((bar) => bar.getBoundingClientRect())
    .filter((box) => box.height > 0);
  const barTop = drawn.length
    ? Math.min(...drawn.map((box) => box.top))
    : columnBox.bottom;
  const above = barTop - frameBox.top - height - 10;
  const center = columnBox.left - frameBox.left + columnBox.width / 2;
  if (above >= 0) {
    // There is room over the bar, so sit above it and stay centred.
    tooltip.style.left = `${clampLeft(center - width / 2)}px`;
    tooltip.style.top = `${above}px`;
    return;
  }
  // A tall bar leaves no headroom. Move beside the column rather than on top of
  // it, so the hovered bar the reader is inspecting is never covered.
  const gap = 12;
  const rightEdge = columnBox.right - frameBox.left + gap;
  const leftEdge = columnBox.left - frameBox.left - gap - width;
  const fitsRight = rightEdge + width <= frame.clientWidth - 8;
  const fitsLeft = leftEdge >= 8;
  const besideTop = () =>
    `${Math.max(
      Math.min(barTop - frameBox.top, frame.clientHeight - tooltip.offsetHeight - 8),
      8,
    )}px`;
  if (fitsRight || fitsLeft) {
    tooltip.style.left = `${clampLeft(fitsRight ? rightEdge : leftEdge)}px`;
    tooltip.style.top = besideTop();
    return;
  }
  // Neither side has room at the card's natural width. Narrow it to whichever
  // side has more space rather than letting it clamp back over the bar; the
  // card is capped in CSS, so this only ever shrinks it further.
  const roomRight = frame.clientWidth - 8 - rightEdge;
  const roomLeft = columnBox.left - frameBox.left - gap - 8;
  const useRight = roomRight >= roomLeft;
  tooltip.style.maxWidth = `${Math.max(Math.round(useRight ? roomRight : roomLeft), 120)}px`;
  tooltip.style.left = `${clampLeft(
    useRight ? rightEdge : columnBox.left - frameBox.left - gap - tooltip.offsetWidth,
  )}px`;
  tooltip.style.top = besideTop();
}

function hideDayTooltip() {
  const tooltip = byId("day-tooltip");
  if (!tooltip) return;
  tooltip.hidden = true;
  tooltip.setAttribute("aria-hidden", "true");
  openTooltipColumn = null;
  document
    .querySelectorAll("#trend-chart .day-column[aria-describedby]")
    .forEach((column) => column.removeAttribute("aria-describedby"));
}

// Escape closes the card without moving focus, so a reader who finds it in the
// way can clear it and keep their place in the column order.
function dismissDayTooltip() {
  if (!openTooltipColumn) return false;
  dismissedTooltipColumn = openTooltipColumn;
  hideDayTooltip();
  return true;
}

// The chart scrolls horizontally, so an open card has to follow its column. A
// column scrolled out of the viewport takes its card with it: on a narrow frame
// the card would otherwise stay pinned at the clamp edge, labelled with a day
// no longer on screen.
function repositionDayTooltip() {
  const tooltip = byId("day-tooltip");
  if (!tooltip || tooltip.hidden || !openTooltipColumn) return;
  const chart = byId("trend-chart");
  const columnBox = openTooltipColumn.getBoundingClientRect();
  const chartBox = chart.getBoundingClientRect();
  if (columnBox.right <= chartBox.left || columnBox.left >= chartBox.right) {
    hideDayTooltip();
    return;
  }
  positionDayTooltip(tooltip, openTooltipColumn);
}

// A pointer leaving, or focus moving on, closes the card only if no day column
// still holds focus. Otherwise the keyboard's card is restored. The check is
// deferred because blur fires before focus settles on the next element, and a
// pointerleave arrives before :hover has updated.
function releaseDayTooltip() {
  hideDayTooltip();
  requestAnimationFrame(() => {
    // An Escape dismissal outlives a pointer moving away: it lifts only once
    // its column is neither hovered nor focused, so taking the mouse off a
    // focused column cannot reopen the card the reader just closed.
    const dismissed = dismissedTooltipColumn;
    if (
      dismissed &&
      document.activeElement !== dismissed &&
      !dismissed.matches(":hover")
    ) {
      dismissedTooltipColumn = null;
    }
    const focused = document.activeElement;
    if (
      focused &&
      focused.classList &&
      focused.classList.contains("day-column") &&
      typeof focused.showDayTooltip === "function" &&
      byId("day-tooltip").hidden
    ) {
      focused.showDayTooltip();
    }
  });
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
      organizations: item.producer ? [item.producer] : [],
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
    byId("organization-filter"),
    [
      ...new Set(
        observations.flatMap((item) => item.organizations || []),
      ),
    ].sort(),
    "organizations",
    state.organization,
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
      item.snapshot_date === state.todayDate &&
      (!state.kind || item.observation_kind === state.kind) &&
      (!state.category || (item.categories || []).includes(state.category)) &&
      (!state.source || item.source === state.source) &&
      (!state.organization || (item.organizations || []).includes(state.organization)) &&
      (!state.event || item.event_kind === state.event) &&
      (!query || haystack.includes(query))
    );
  });
}

// When a record is supplied, the rubric is rendered with that record's own
// component scores beside each weight, so the reader can see the arithmetic
// that produced the total rather than a generic description of it.
// versionOverride opens a specific rubric version (e.g. from a #rubric=1
// deep link) without implying a record's own scores are being shown.
function openRubric(item = null, versionOverride = null) {
  const data = versionOverride
    ? state.data?.rubrics?.[String(versionOverride)] || rubricFor(item)
    : rubricFor(item);
  const dialog = byId("rubric-dialog");
  if (!data) return;
  const max = Number(data.score_max) || 4;
  const components = data.components || [];
  const contribution = (component) =>
    Number(item?.[`${component.key}_score`] || 0) * Number(component.weight || 0);

  // Two rubrics are in circulation on different scales (v1 tops out at 4, v2 at
  // 100). A dialog that says only "0 to 4" leaves a reader who has read the
  // README's 0-100 rubric unable to tell whether the number is wrong or simply
  // older, so the version is named rather than implied.
  const version = Number(data.scoring_version) || 1;
  const current = Number(state.data?.rubric?.scoring_version) || version;
  const isLegacy = version !== current;
  state.rubric = String(version);
  writeUrl();
  const header = [
    element("p", {
      className: "detail-source",
      text: `Scoring rubric v${version}${isLegacy ? " · superseded" : " · current"}`,
    }),
    element("h2", {
      className: "detail-title rubric-title",
      text: "How priority is scored",
      attrs: { id: "rubric-title" },
    }),
    element("p", {
      className: "detail-summary",
      text:
        `Priority is the weighted mean of four components, each measured on a 0 to ${max.toFixed(2)} ` +
        "scale. Every number below is read from the same definition the pipeline applies.",
    }),
    ...(isLegacy
      ? [
          element("p", {
            className: "discovery-note",
            text:
              (item
                ? `This record was scored by rubric v${version} on a 0 to ${max.toFixed(2)} scale. `
                : `Rubric v${version} scored records on a 0 to ${max.toFixed(2)} scale. `) +
              `The current rubric is v${current} on a 0 to ` +
              `${(Number(state.data?.rubric?.score_max) || 100).toFixed(2)} scale. Scores from the ` +
              "two versions are not directly comparable, and past records are not rescored.",
          }),
        ]
      : []),
    element("p", { className: "rubric-formula", text: data.formula }),
  ];

  if (item) {
    header.push(
      element("div", { className: "rubric-worked" }, [
        element("strong", { text: `This record scores ${Number(item.total_score || 0).toFixed(2)}` }),
        element("p", {
          text: components
            .map(
              (component) =>
                `${component.weight.toFixed(2)} x ${Number(
                  item[`${component.key}_score`] || 0,
                ).toFixed(2)} ${component.label.toLowerCase()}`,
            )
            .join("  +  "),
        }),
      ]),
    );
  }

  const componentSections = components.map((component) =>
    element("section", { className: "rubric-component" }, [
      element("div", { className: "rubric-component-head" }, [
        element("h3", { text: component.label }),
        element("span", {
          className: "rubric-weight",
          text: `weight ${component.weight.toFixed(2)}`,
        }),
      ]),
      element("p", { text: component.summary }),
      element(
        "ul",
        { className: "rubric-bands" },
        (component.bands || []).map((band) => element("li", { text: band })),
      ),
      item
        ? element("p", { className: "rubric-contribution" }, [
            element("span", {
              text:
                `Scored ${Number(item[`${component.key}_score`] || 0).toFixed(2)}` +
                ` · contributes ${contribution(component).toFixed(2)} to the total`,
            }),
          ])
        : null,
    ]),
  );

  const limits =
    (data.limits || []).length
      ? element("section", { className: "rubric-limits" }, [
          element("h3", { text: "What this score does not claim" }),
          element(
            "ul",
            {},
            data.limits.map((limit) => element("li", { text: limit })),
          ),
        ])
      : null;

  const cutoff =
    data.minimum_score !== undefined && data.minimum_score !== null
      ? element("p", {
          className: "discovery-note",
          text:
            `A record is reported only if it matches at least one taxonomy category and ` +
            `scores ${Number(data.minimum_score).toFixed(2)} or above, or if it names a ` +
            "watchlisted artifact, which is published regardless of score.",
        })
      : null;

  replaceChildren(byId("rubric-content"), [
    ...header,
    ...componentSections,
    limits,
    cutoff,
    element("div", { className: "detail-links" }, [
      element("a", {
        className: "secondary-link",
        text: "Read the scoring code ↗",
        attrs: {
          href: "https://github.com/ktwu01/benchmark-radar/blob/main/src/benchmark_radar/rubric.py",
          target: "_blank",
          rel: "noopener noreferrer",
        },
      }),
    ]),
  ]);
  dialog.showModal();
}

function expandedRecord(item, teaser) {
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
        ["Relevance", Number(item.relevance_score || 0).toFixed(2)],
        ["Evidence", Number(item.evidence_score || 0).toFixed(2)],
        ["Recency", Number(item.recency_score || 0).toFixed(2)],
        // Adoption is weighted into the total, so hiding it here left the
        // four shown components unable to explain the priority above them.
        ["Adoption", Number(item.adoption_score || 0).toFixed(2)],
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
      text: isAttention
        ? "Open public discussion ↗"
        : item.source === "Hugging Face"
          ? "Read full card ↗"
          : "Open primary source ↗",
      attrs: { href: item.url, target: "_blank", rel: "noopener noreferrer" },
    }),
  ]);
  return element("div", { className: "record-detail" }, [
    element("p", {
      className: "detail-source",
      text: `${item.source} · ${item.event_kind} · ${item.snapshot_date}`,
    }),
    element("p", {
      className: item.summary ? "detail-summary" : "detail-summary signal-nodesc",
      text: item.summary
        ? teaser
          ? summaryRemainder(item.summary, teaser) || "No further description beyond the preview above."
          : item.summary
        : "No description published at the source.",
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
}

function mapFilterFor(entity) {
  state.q = "";
  state.kind = "evidence";
  state.category = "";
  state.source = "";
  state.organization = "";
  state.event = "";
  if (entity.type === "artifact") {
    state.q = entity.label;
    state.todayDate = entity.last_seen_at;
  } else if (entity.type === "topic") {
    state.category = entity.id.replace(/^topic:/, "");
  } else if (entity.type === "source") {
    state.source = entity.label;
  } else if (entity.type === "organization") {
    state.organization = entity.label;
  }
}

function selectMapNode(entity, relatedEntities) {
  state.entity = entity.id;
  mapFilterFor(entity);
  const topicAggregate = (state.data.corpus.aggregates.topics || []).find(
    (entry) => `topic:${entry.topic}` === entity.id,
  );
  const stats = [
    definition("Type", entity.type),
    definition("First seen", formatDate(entity.first_seen_at, { dateStyle: "medium" })),
    definition("Last seen", formatDate(entity.last_seen_at, { dateStyle: "medium" })),
    definition("Observed days", Number(entity.seen_days?.length || 0).toLocaleString()),
    ...(entity.type === "artifact"
      ? [
          definition("Observations", Number(entity.observation_count || 0).toLocaleString()),
          definition(
            "Latest priority",
            entity.latest_score === null || entity.latest_score === undefined
              ? "not scored"
              : Number(entity.latest_score).toFixed(2),
          ),
        ]
      : []),
    ...(topicAggregate
      ? [
          definition("Artifact count", topicAggregate.entity_count),
          definition("Source breadth", topicAggregate.source_breadth),
          // The window is nominally 7 days but divides by the days actually
          // observed, so early in the archive "7-day" named a span that does
          // not exist yet. The label states the span that was measured.
          definition(
            `${
              state.data.corpus.aggregates.observed_window_days ??
              state.data.corpus.aggregates.window_days
            }-day velocity`,
            topicAggregate.velocity === null
              ? "needs a prior window"
              : `${topicAggregate.velocity >= 0 ? "+" : ""}${topicAggregate.velocity}/day`,
          ),
        ]
      : []),
  ];
  const viewResults = element("button", {
    className: "primary-link map-view-results",
    text: "View matching observations →",
    attrs: { type: "button" },
  });
  viewResults.addEventListener("click", () => {
    setView("today");
    renderToday();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  replaceChildren(byId("map-detail"), [
    element("p", { className: "eyebrow", text: "Selected node" }),
    element("h2", { text: entity.label }),
    element("p", {
      text:
        entity.type === "artifact"
          ? "The corresponding date and exact title search are now set for Today."
          : `The ${entity.type} filter is now set for Today.`,
    }),
    element("dl", {}, stats),
    relatedEntities.length
      ? element("p", {
          className: "discovery-note",
          text: `Connected to ${relatedEntities
            .slice(0, 8)
            .map((related) => related.label)
            .join(", ")}${relatedEntities.length > 8 ? "…" : ""}`,
        })
      : null,
    viewResults,
    entity.url
      ? element("a", {
          className: "primary-link",
          text: "Open primary source ↗",
          attrs: {
            href: entity.url,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        })
      : null,
  ]);
  writeUrl();
}

function rankedCounts(values, limit = 6) {
  return Object.entries(values || {})
    .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0) || a[0].localeCompare(b[0]))
    .slice(0, limit);
}

function mapInsightCard(title, entries, emptyText) {
  return element("article", { className: "map-insight-card" }, [
    element("h2", { text: title }),
    entries.length
      ? element(
          "ul",
          {},
          entries.map(([label, value]) =>
            element("li", {}, [
              element("span", { text: label }),
              element("strong", { text: value }),
            ]),
          ),
        )
      : element("p", { text: emptyText }),
  ]);
}

function renderMapInsights(corpus) {
  const aggregates = corpus.aggregates || {};
  const entityTypes = aggregates.entity_types || {};
  const topicEntries = (aggregates.topics || [])
    .sort(
      (a, b) =>
        Number(b.entity_count || 0) - Number(a.entity_count || 0) ||
        a.topic.localeCompare(b.topic),
    )
    .map((topic) => [
      topic.topic.replaceAll("_", " "),
      `${metricLabel(topic.entity_count, "artifact")} · ${metricLabel(
        topic.source_breadth,
        "source",
      )}`,
    ]);
  const sourceEntries = rankedCounts(aggregates.sources).map(([source, count]) => [
    source,
    metricLabel(count, "observation"),
  ]);
  const organizationEntries = rankedCounts(aggregates.organizations).map(
    ([organization, count]) => [organization, metricLabel(count, "observation")],
  );
  const coverageEntries = [
    ["Artifacts", Number(entityTypes.artifact || 0).toLocaleString()],
    ["Organizations", Number(entityTypes.organization || 0).toLocaleString()],
    ["Authors", Number(entityTypes.person || 0).toLocaleString()],
    ["Discovery sources", Number(entityTypes.source || 0).toLocaleString()],
    ["Topics", Number(entityTypes.topic || 0).toLocaleString()],
  ];
  replaceChildren(byId("map-insights"), [
    mapInsightCard("Corpus coverage", coverageEntries, "No corpus entities yet."),
    mapInsightCard("Topic coverage", topicEntries, "No topics assigned yet."),
    mapInsightCard("Discovery sources", sourceEntries, "No discovery sources yet."),
    mapInsightCard(
      "Most represented organizations",
      organizationEntries,
      "No organizations identified yet.",
    ),
  ]);
}

// --- Model Card Adoption Rank (issue #83) -----------------------------------
//
// Counts how many curated model cards report each benchmark. The count is per
// document, so a card reporting AIME in four configurations contributes the
// same single adoption as a card reporting it once. That is the whole reason
// this ranking is publishable while a score table is not: a mention survives
// every reasoning-budget and pass@k caveat that makes two reported scores
// incomparable.

// Cut points for the benchmark release-date filter. Chosen as era boundaries
// rather than rolling windows so a bookmarked URL keeps meaning the same thing
// next month: "?lera=2026" is always "released in 2026", never "the last N
// months". A benchmark with no recorded release date is excluded by any era
// filter, which is the honest outcome -- it cannot be placed on the timeline.
// "Released in 2026" is bounded at both ends. An open-ended lower bound would
// silently absorb 2027 benchmarks the moment one is added, contradicting both
// the label and the permalink promise. "2025 or later" says "or later" and is
// therefore correctly open-ended.
const LEADERBOARD_ERAS = [
  { value: "2026", label: "Released in 2026", from: "2026-01-01", to: "2027-01-01" },
  { value: "2025", label: "Released 2025 or later", from: "2025-01-01" },
  { value: "pre2024", label: "Released before 2024", to: "2024-01-01" },
];

function leaderboardEntries() {
  const board = state.data?.model_card_leaderboard;
  if (!board) return [];
  const query = state.lq.trim().toLowerCase();
  const era = LEADERBOARD_ERAS.find((candidate) => candidate.value === state.lera);
  return (board.entries || []).filter((entry) => {
    if (state.ldomain && entry.domain !== state.ldomain) return false;
    if (state.lorg && !(entry.organizations || []).includes(state.lorg)) return false;
    if (era) {
      // ISO dates compare correctly as strings, so no Date parsing is needed
      // and no timezone can shift a benchmark across a year boundary.
      if (!entry.released) return false;
      if (era.from && entry.released < era.from) return false;
      if (era.to && entry.released >= era.to) return false;
    }
    if (!query) return true;
    const haystack = [entry.name, entry.benchmark_id, ...(entry.aliases || [])]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function adoptionBar(entry, maxCount) {
  // The 2% floor keeps a single-card benchmark from rendering as an empty
  // track, but it must not apply to a zero: a visible bar beside a count of 0
  // contradicts the number it is supposed to encode.
  const width =
    maxCount && entry.card_count
      ? Math.max(2, Math.round((entry.card_count / maxCount) * 100))
      : 0;
  return element(
    "div",
    {
      className: "adoption-bar",
      attrs: {
        role: "img",
        "aria-label": `${metricLabel(entry.card_count, "model card")} of ${metricLabel(
          state.data.model_card_leaderboard.model_card_count,
          "model card",
        )}`,
      },
    },
    [
      element("span", {
        className: "adoption-bar-fill",
        attrs: { style: `width: ${width}%` },
      }),
    ],
  );
}

function leaderboardRow(entry) {
  const board = state.data.model_card_leaderboard;
  const maxCount = board.entries?.[0]?.card_count || 0;
  const header = element("summary", { className: "record-summary" }, [
    element("span", {
      className: "signal-rank",
      text: String(entry.rank).padStart(2, "0"),
    }),
    element("div", { className: "record-heading" }, [
      element("div", { className: "signal-meta" }, [
        element("span", { text: entry.domain.replaceAll("_", " ") }),
        // A benchmark in the registry that no curated card reports is a real
        // observation, not an empty row: it says the benchmark is discussed
        // without yet being adopted in vendor reporting. Say that, rather than
        // showing a bare "0 organizations of 8".
        entry.card_count
          ? element("span", {
              text: `${metricLabel(entry.organization_count, "organization")} of ${
                board.organization_count
              }`,
            })
          : element("span", { text: "not yet reported in these cards" }),
        // The instrument's own age, which the adoption count deliberately does
        // not encode: a 2020 benchmark with 9 cards and a 2026 benchmark with 9
        // cards are very different findings about vendor reporting.
        entry.released
          ? element("span", {
              text: `released ${formatDate(entry.released, { dateStyle: "medium" })}`,
            })
          : null,
      ]),
      element("h3", { text: entry.name }),
      // The caveat is part of the row, not a footnote. A ranking that puts a
      // saturated benchmark near the top without saying so is misleading in
      // exactly the direction issue #83 warns about.
      entry.caveat ? element("p", { className: "signal-tldr", text: entry.caveat }) : null,
    ]),
    element("div", { className: "score" }, [
      element("div", { className: "score-value" }, [
        element("strong", { text: String(entry.card_count) }),
        element("span", { text: `/ ${board.model_card_count}` }),
      ]),
      adoptionBar(entry, maxCount),
      element("p", { className: "score-label", text: "Model cards" }),
    ]),
  ]);

  const adopters = element(
    "ul",
    { className: "adopter-list" },
    (entry.adopters || []).map((adopter) =>
      element("li", {}, [
        // A plain text link, not the .primary-link call-to-action button: a
        // twelve-row roster of dark blocks reads as twelve competing actions
        // rather than as one list of sources.
        element("a", {
          className: "adopter-link",
          text: `${adopter.organization} · ${adopter.model}`,
          attrs: {
            href: adopter.url,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        }),
        element("span", {
          className: "adopter-meta",
          text: `${String(adopter.document_type).replaceAll("_", " ")}${
            adopter.published ? ` · ${formatDate(adopter.published, { dateStyle: "medium" })}` : ""
          }`,
        }),
      ]),
    ),
  );

  return element("details", { className: "record-card" }, [
    header,
    element("div", { className: "record-detail" }, [
      element("h3", { text: "Reported by" }),
      adopters,
      entry.url
        ? element("a", {
            className: "primary-link",
            text: "Benchmark home ↗",
            attrs: { href: entry.url, target: "_blank", rel: "noopener noreferrer" },
          })
        : null,
    ]),
  ]);
}

function renderLeaderboardFilters(board) {
  // Every domain present in the ranking, not board.domains: that summary counts
  // only adopted benchmarks, so a domain whose benchmarks are all unadopted
  // would be listed in the table with no way to filter to it.
  const domains = [...new Set((board.entries || []).map((entry) => entry.domain))].sort();
  replaceChildren(byId("leaderboard-domain"), [
    option("", "All domains", !state.ldomain),
    ...domains.map((domain) =>
      option(domain, domain.replaceAll("_", " "), domain === state.ldomain),
    ),
  ]);
  const organizations = Object.keys(board.organizations || {}).sort();
  replaceChildren(byId("leaderboard-organization"), [
    option("", "All organizations", !state.lorg),
    ...organizations.map((organization) =>
      option(organization, organization, organization === state.lorg),
    ),
  ]);
  replaceChildren(byId("leaderboard-era"), [
    option("", "Any release date", !state.lera),
    ...LEADERBOARD_ERAS.map((era) => option(era.value, era.label, era.value === state.lera)),
  ]);
  if (byId("leaderboard-search").value !== state.lq) {
    byId("leaderboard-search").value = state.lq;
  }
}

function renderLeaderboard() {
  const board = state.data?.model_card_leaderboard;
  const navButton = document.querySelector('[data-view="leaderboard"]');
  // A checkout without the curated registry publishes no ranking. Hiding the
  // nav entry is the honest response: offering a tab that opens an empty page
  // reads as a broken feature rather than as absent data.
  if (!board) {
    if (navButton) navButton.hidden = true;
    return;
  }
  if (navButton) navButton.hidden = false;

  byId("leaderboard-measures").textContent = board.measures || "";
  renderLeaderboardFilters(board);

  const topEntries = (board.entries || []).filter((entry) => entry.card_count > 0);
  replaceChildren(byId("leaderboard-insights"), [
    mapInsightCard(
      "Registry coverage",
      [
        ["Model cards", Number(board.model_card_count || 0).toLocaleString()],
        ["Organizations", Number(board.organization_count || 0).toLocaleString()],
        ["Benchmarks tracked", Number(board.benchmark_count || 0).toLocaleString()],
        ["Reported at least once", Number(topEntries.length).toLocaleString()],
      ],
      "No registry entries yet.",
    ),
    mapInsightCard(
      "Cards per organization",
      Object.entries(board.organizations || {})
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([organization, count]) => [organization, metricLabel(count, "card")]),
      "No organizations in the registry yet.",
    ),
    // Counts only benchmarks at least one card reports, which is deliberately
    // narrower than the domain filter below. A benchmark tracked but reported
    // by nobody is a real finding about the registry, so it stays visible in
    // the list while being excluded from "how much of this domain is in use".
    mapInsightCard(
      "Domains reported at least once",
      Object.entries(board.domains || {})
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([domain, count]) => [
          domain.replaceAll("_", " "),
          metricLabel(count, "benchmark"),
        ]),
      "No domains represented yet.",
    ),
    mapInsightCard(
      "Adopted by every organization",
      topEntries
        .filter((entry) => entry.organization_count === board.organization_count)
        .map((entry) => [entry.name, metricLabel(entry.card_count, "card")]),
      "No benchmark is reported by every organization in the registry.",
    ),
  ]);

  const entries = leaderboardEntries();
  byId("leaderboard-count").textContent = `${metricLabel(
    entries.length,
    "benchmark",
  )} of ${board.entries.length}`;
  replaceChildren(
    byId("leaderboard-list"),
    entries.length
      ? entries.map(leaderboardRow)
      : [
          element("p", {
            className: "empty-state",
            text: "No benchmarks match these filters. Clear one or more filters to widen the view.",
          }),
        ],
  );

  const cards = board.model_cards || [];
  byId("leaderboard-cards-count").textContent = metricLabel(cards.length, "document");
  replaceChildren(byId("leaderboard-cards"), cards.map(modelCardRow));
}

// The reverse direction of the registry's dual link, rendered as a disclosure so
// a reader can audit one card against its source document. The forward direction
// (a benchmark, expanded to its adopters) answers "who reports this?"; this
// answers "what did this card report?", which is the question you need when
// checking our data against the ground-truth PDF or blog post. Both are built
// from the same edge set in `adoption_rank`, so what is listed here is exactly
// what that card contributes to every count in the table above.
function modelCardRow(card) {
  const benchmarks = card.reported_benchmarks || [];
  // `record-summary-unranked` selects the three-column grid: these rows carry no
  // rank number, unlike the ranked benchmark rows above.
  const summary = element("summary", { className: "record-summary record-summary-unranked" }, [
    element("div", { className: "record-heading" }, [
      element("div", { className: "signal-meta" }, [
        element("span", { text: card.organization }),
        element("span", { text: String(card.document_type).replaceAll("_", " ") }),
        element("span", {
          text: card.published
            ? formatDate(card.published, { dateStyle: "medium" })
            : "date unknown",
        }),
      ]),
      element("h3", { text: card.model }),
    ]),
    element("div", { className: "score" }, [
      element("div", { className: "score-value" }, [
        element("strong", { text: String(card.benchmark_count) }),
      ]),
      element("p", { className: "score-label", text: "Benchmarks" }),
    ]),
  ]);

  // Grouped by domain because that is how the source documents are laid out:
  // a card's own tables are sectioned into reasoning, coding, agentic and
  // multimodal blocks, so grouping the same way keeps a side-by-side check
  // against the PDF a matter of reading down one column.
  const byDomain = new Map();
  for (const benchmark of benchmarks) {
    if (!byDomain.has(benchmark.domain)) byDomain.set(benchmark.domain, []);
    byDomain.get(benchmark.domain).push(benchmark);
  }

  const groups = [...byDomain.entries()].map(([domain, items]) =>
    element("div", { className: "card-benchmark-group" }, [
      element("h4", { text: domain.replaceAll("_", " ") }),
      element(
        "ul",
        { className: "adopter-list" },
        items.map((benchmark) =>
          element("li", {}, [
            benchmark.url
              ? element("a", {
                  className: "adopter-link",
                  text: benchmark.name,
                  attrs: {
                    href: benchmark.url,
                    target: "_blank",
                    rel: "noopener noreferrer",
                  },
                })
              : element("span", { className: "adopter-link", text: benchmark.name }),
            element("span", {
              className: "adopter-meta",
              text: benchmark.released
                ? `released ${formatDate(benchmark.released, { dateStyle: "medium" })}`
                : "release date unrecorded",
            }),
          ]),
        ),
      ),
    ]),
  );

  return element("details", { className: "record-card" }, [
    summary,
    element("div", { className: "record-detail" }, [
      element("h3", { text: "Benchmarks this document reports" }),
      element("p", {
        className: "section-note",
        // Says what the reader is and is not looking at, at the point of
        // looking. A mention is not a score, and the expanded list would
        // otherwise read as if it were an extract of the card's results table.
        text:
          "Every benchmark this document puts in front of readers, counted once each. " +
          "These are mentions, not scores: the source records the configuration, and " +
          "this registry deliberately does not.",
      }),
      ...groups,
      element("a", {
        className: "primary-link",
        text: "Open source document ↗",
        attrs: { href: card.url, target: "_blank", rel: "noopener noreferrer" },
      }),
      card.retrieved_at
        ? element("p", {
            className: "adopter-meta",
            text: `Last read by a human on ${formatDate(card.retrieved_at, {
              dateStyle: "medium",
            })}`,
          })
        : null,
    ]),
  ]);
}

function renderTrendMap() {
  const corpus = state.data.corpus;
  if (!corpus) return;
  const entityById = new Map(corpus.entities.map((entity) => [entity.id, entity]));
  const selectedFromUrl = entityById.get(state.entity);
  const artifacts = corpus.entities
    .filter((entity) => entity.type === "artifact")
    .sort(
      (a, b) =>
        Number(b.latest_score || 0) - Number(a.latest_score || 0) ||
        Number(b.observation_count || 0) - Number(a.observation_count || 0) ||
        a.label.localeCompare(b.label),
    );
  const artifactOrder = new Map(
    artifacts.map((entity, index) => [entity.id, index]),
  );
  const artifactIds = new Set(artifacts.map((entity) => entity.id));
  const visibleEdges = corpus.edges.filter(
    (edge) =>
      artifactIds.has(edge.source) &&
      ["HAS_TOPIC", "RELEASED_BY", "FOUND_VIA"].includes(edge.type),
  );
  const visibleIds = new Set([
    ...artifactIds,
    ...visibleEdges.flatMap((edge) => [edge.source, edge.target]),
  ]);
  if (
    selectedFromUrl &&
    ["topic", "organization", "source"].includes(selectedFromUrl.type)
  ) {
    visibleIds.add(selectedFromUrl.id);
  }
  const visibleEntities = [...visibleIds]
    .map((id) => entityById.get(id))
    .filter(Boolean);
  const typeOrder = ["source", "organization", "artifact", "topic"];
  const xByType = { source: 110, organization: 350, artifact: 650, topic: 1010 };
  const groups = Object.fromEntries(
    typeOrder.map((type) => [
      type,
      visibleEntities
        .filter((entity) => entity.type === type)
        .sort((a, b) =>
          type === "artifact"
            ? artifactOrder.get(a.id) - artifactOrder.get(b.id)
            : a.label.localeCompare(b.label),
        ),
    ]),
  );
  const rowSpacing = 36;
  const height = Math.max(
    560,
    groups.artifact.length * rowSpacing + 120,
  );
  const positions = new Map();
  typeOrder.forEach((type) => {
    groups[type].forEach((entity, index) => {
      const y =
        type === "artifact"
          ? 70 + index * rowSpacing
          : groups[type].length === 1
            ? height / 2
            : 70 + (index * (height - 140)) / (groups[type].length - 1);
      positions.set(entity.id, { x: xByType[type], y });
    });
  });

  const svg = svgElement("svg", {
    viewBox: `0 0 1200 ${height}`,
    width: "1200",
    height,
    role: "img",
    "aria-label": "Artifact nodes connected to topics, organizations, and discovery sources",
  });
  typeOrder.forEach((type) => {
    svg.append(
      svgElement(
        "text",
        {
          x: xByType[type],
          y: 30,
          "text-anchor": "middle",
          class: "map-column-label",
        },
        `${type}s`,
      ),
    );
  });
  visibleEdges.forEach((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return;
    svg.append(
      svgElement("line", {
        x1: source.x,
        y1: source.y,
        x2: target.x,
        y2: target.y,
        class: "map-edge",
      }),
    );
  });
  visibleEntities.forEach((entity) => {
    const position = positions.get(entity.id);
    if (!position) return;
    const group = svgElement("g", {
      class: `map-node map-node-${entity.type}`,
      transform: `translate(${position.x} ${position.y})`,
      tabindex: "0",
      role: "button",
      "aria-label": `${entity.type}: ${entity.label}`,
    });
    group.append(svgElement("circle", { r: entity.type === "artifact" ? 8 : 6 }));
    group.append(
      svgElement(
        "text",
        { x: 14, y: 4 },
        shorten(entity.label, entity.type === "artifact" ? 38 : 24),
      ),
    );
    const related = visibleEdges
      .filter((edge) => edge.source === entity.id || edge.target === entity.id)
      .map((edge) => entityById.get(edge.source === entity.id ? edge.target : edge.source))
      .filter(Boolean);
    const select = () => selectMapNode(entity, related);
    group.addEventListener("click", select);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    svg.append(group);
  });
  renderMapInsights(corpus);
  replaceChildren(byId("map-canvas"), [svg]);
  const authorCount = Number(corpus.aggregates?.entity_types?.person || 0);
  byId("map-summary").textContent =
    `Showing all ${artifacts.length.toLocaleString()} artifacts · ` +
    `${groups.organization.length.toLocaleString()} organizations · ` +
    `${groups.source.length.toLocaleString()} sources · ${groups.topic.length.toLocaleString()} topics` +
    (authorCount
      ? ` · ${authorCount.toLocaleString()} author nodes summarized above and omitted from the canvas`
      : "");
  if (selectedFromUrl) {
    const related = corpus.edges
      .filter(
        (edge) => edge.source === selectedFromUrl.id || edge.target === selectedFromUrl.id,
      )
      .map((edge) =>
        entityById.get(
          edge.source === selectedFromUrl.id ? edge.target : edge.source,
        ),
      )
      .filter(Boolean);
    selectMapNode(selectedFromUrl, related);
  }
}

function attentionActivity(item) {
  return element("div", { className: "attention-activity" }, [
    element("strong", { text: metricLabel(item.metrics?.points, "point") }),
    element("span", { text: metricLabel(item.metrics?.comments, "comment") }),
    element("span", { text: metricLabel(item.metrics?.submissions ?? 1, "submission") }),
  ]);
}

function observationCard(item, index) {
  const isAttention = item.observation_kind === "attention";
  const metadata = isAttention
    ? element("div", { className: "signal-meta" }, [
        element("span", { className: "attention-badge", text: "attention" }),
        element("span", { text: `${item.source} · ${item.event_kind}` }),
      ])
    : pillBar(item);
  const summary = (item.summary || "").trim()
    ? shorten(item.summary)
    : "No description published at the source.";
  const header = element("summary", { className: "record-summary" }, [
    element("span", {
      className: "signal-rank",
      text: String(index + 1).padStart(2, "0"),
    }),
    element("div", { className: "record-heading" }, [
      metadata,
      element("h3", { text: item.title }),
      ...(item.watchlist && item.watchlist_note
        ? [element("p", { className: "signal-tldr", text: item.watchlist_note })]
        : []),
      element("p", {
        className: item.summary ? "" : "signal-nodesc",
        text: isAttention
          ? `${summary} · ${metricLabel(item.metrics?.points, "point")}`
          : summary,
      }),
    ]),
    isAttention ? attentionActivity(item) : scoreBlock(item),
  ]);
  return element(
    "details",
    {
      className: `record-card${isAttention ? " attention-card" : ""}`,
    },
    [header, expandedRecord(item, (item.summary || "").trim() ? summary : "")],
  );
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      setView(button.dataset.view);
      if (button.dataset.view === "today") renderToday();
      if (button.dataset.view === "leaderboard") renderLeaderboard();
      if (button.dataset.view === "trends") renderTrends();
      if (button.dataset.view === "map") renderTrendMap();
    });
  });
  // Reads every control rather than the event target, so the <select>
  // "input"-before-"change" ordering that broke the Scan date picker (issue
  // #43) cannot write a stale value back over the reader's pick here: whichever
  // event arrives first, all three values come from the DOM as it stands now.
  byId("leaderboard-filters").addEventListener("input", () => {
    state.lq = byId("leaderboard-search").value;
    state.ldomain = byId("leaderboard-domain").value;
    state.lorg = byId("leaderboard-organization").value;
    state.lera = byId("leaderboard-era").value;
    renderLeaderboard();
    writeUrl();
  });
  byId("leaderboard-clear").addEventListener("click", () => {
    state.lq = "";
    state.ldomain = "";
    state.lorg = "";
    state.lera = "";
    byId("leaderboard-search").value = "";
    renderLeaderboard();
    writeUrl();
  });
  byId("today-date").addEventListener("change", (event) => {
    state.todayDate = event.target.value;
    renderToday();
  });
  byId("trend-released-only").addEventListener("change", (event) => {
    state.trendReleasedOnly = event.target.checked;
    renderTrends();
  });
  // An open hover card is positioned against the chart, so any scroll or resize
  // that moves its column has to move it too.
  byId("trend-chart").addEventListener("scroll", repositionDayTooltip, {
    passive: true,
  });
  window.addEventListener("resize", repositionDayTooltip);
  document.addEventListener("keydown", (event) => {
    // Do not swallow Escape unless a card is actually open to close.
    if (event.key === "Escape" && dismissDayTooltip()) event.preventDefault();
  });
  byId("filters").addEventListener("input", (event) => {
    // The Scan date select has its own dedicated change handler above. A
    // <select> fires "input" before "change", and this bubbled "input"
    // reaching here would call renderToday() with the still-stale
    // state.todayDate, which then writes the OLD date back onto the
    // control and clobbers the user's just-made selection.
    if (event.target === byId("today-date")) return;
    state.q = byId("search-filter").value;
    state.kind = byId("kind-filter").value;
    state.category = byId("category-filter").value;
    state.source = byId("source-filter").value;
    state.organization = byId("organization-filter").value;
    state.event = byId("event-filter").value;
    renderToday();
  });
  // Both filter panels are <form>s whose state lives in the URL query we
  // build ourselves. Enter in a search field would otherwise trigger an
  // implicit GET that submits only the named controls, dropping `view` and
  // reloading the reader into Today from whichever panel they were using.
  document.querySelectorAll("#filters, #leaderboard-filters").forEach((form) => {
    form.addEventListener("submit", (event) => event.preventDefault());
  });
  byId("clear-filters").addEventListener("click", () => {
    state.q = "";
    state.kind = "";
    state.category = "";
    state.source = "";
    state.organization = "";
    state.event = "";
    renderToday();
  });
  byId("rubric-close").addEventListener("click", () => byId("rubric-dialog").close());
  byId("rubric-dialog").addEventListener("click", (event) => {
    if (event.target === byId("rubric-dialog")) byId("rubric-dialog").close();
  });
  // Fires for every close path (button, backdrop click, Esc), so #rubric is
  // cleared from the URL no matter how the reader dismisses the dialog.
  byId("rubric-dialog").addEventListener("close", () => {
    state.rubric = "";
    writeUrl();
  });
  // Reachable without a record in hand, for a reader who wants the method
  // before they trust any single row.
  byId("rubric-nav").addEventListener("click", () => openRubric());
}

const REPO_SLUG = "ktwu01/benchmark-radar";

// The visible badge reads "★ Star 12", which a screen reader would announce as
// a bare statistic. The accessible name states the action and keeps the count
// as context, so the control sounds like the invitation it is.
const BADGE_ACTIONS = {
  "badge-stars": (count) => `Star this repository on GitHub. ${count} stars`,
  "badge-forks": (count) => `Fork this repository on GitHub. ${count} forks`,
  "badge-issues": (count) => `Open a new issue on GitHub. ${count} issues open`,
};

function setBadgeCount(id, value) {
  const badge = byId(id);
  const node = badge?.querySelector("[data-count]");
  if (!node) return;
  const count = Number(value || 0).toLocaleString();
  node.textContent = count;
  badge.setAttribute("aria-label", BADGE_ACTIONS[id](count));
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
    // open_issues_count includes pull requests, so building the count from it
    // overstates how many issues are actually open. Ask search for issues only,
    // and leave the badge blank if that fails rather than showing the inflated
    // number.
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

// Two scheduled runs a day (issue #44), roughly 6h apart; a gap past 30h
// means both the scheduled run and its same-day retry were missed.
const STALE_AFTER_HOURS = 30;

function renderStaleBanner() {
  const banner = byId("stale-banner");
  const latestDay = state.data.days[state.data.days.length - 1];
  const generatedAt = new Date(state.data.generated_at);
  const ageHours = (Date.now() - generatedAt.getTime()) / 3_600_000;
  const degraded = !latestDay.required_coverage_complete;
  if (ageHours <= STALE_AFTER_HOURS && !degraded) {
    banner.hidden = true;
    banner.textContent = "";
    banner.classList.remove("stale-banner-degraded");
    return;
  }
  const parts = [];
  if (ageHours > STALE_AFTER_HOURS) {
    parts.push(
      `Latest snapshot is from ${formatDate(state.data.generated_at, {
        dateStyle: "medium",
        timeStyle: "short",
      })} UTC (${Math.floor(ageHours)}h ago) — the scheduled run may have failed.`,
    );
  }
  if (degraded) {
    parts.push(
      `Required source failures on ${latestDay.date}: ` +
        `${latestDay.required_coverage_gaps.join(", ")}.`,
    );
  }
  banner.textContent = parts.join(" ");
  banner.classList.toggle("stale-banner-degraded", degraded);
  banner.hidden = false;
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
    renderLeaderboard();
    renderTrends();
    renderTrendMap();
    // A permalink to ?view=leaderboard on a build without the curated registry
    // has nothing to show, so fall back to Today rather than opening a blank
    // section behind a nav entry that renderLeaderboard just hid.
    if (state.view === "leaderboard" && !state.data.model_card_leaderboard) {
      state.view = "today";
    }
    setView(state.view, false);
    byId("build-meta").textContent = `Updated ${formatDate(state.data.generated_at, {
      dateStyle: "medium",
      timeStyle: "short",
    })} UTC`;
    renderStaleBanner();
    if (state.rubric && state.data.rubrics?.[state.rubric]) {
      openRubric(null, state.rubric);
    }
  } catch (error) {
    document.querySelectorAll(".view").forEach((section) => {
      section.hidden = true;
    });
    byId("error-state").hidden = false;
    console.error(error);
  }
}

initialize();
