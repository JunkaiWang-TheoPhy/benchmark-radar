// Client behavior for the generated blog pages.
//
// The chrome around the reading pane is extracted from site/index.html at
// build time, so this script lights up exactly the bits the dashboard's
// app.js would have handled — with the same visible contracts: the language
// toggle flips title, glyph, and aria-pressed; the repository badges fill
// their counts from the same GitHub endpoints; the footer share control uses
// navigator.share with a clipboard fallback.
//
// The body's language blocks stay a pure visibility change and never a fetch.
// Pages without a stored translation ship no toggle at all: a control that
// switches to identical text is broken, and translating here would publish
// text nobody reviewed.
//
// The stored preference is shared with the dashboard under the same key, so a
// reader who chose 中文 there keeps it here. Only an explicit click writes to
// it. Falling back to English on an untranslated brief must not quietly reset
// the preference the reader set somewhere else.
const LANG_STORAGE_KEY = "benchmark-radar:lang";
const LANGS = ["en", "zh"];

function savedLanguage() {
  const param = new URLSearchParams(window.location.search).get("lang");
  if (LANGS.includes(param)) return param;
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (LANGS.includes(saved)) return saved;
  } catch (_) {
    // Storage can be unavailable in private browsing and text-only readers.
  }
  return "en";
}

function showLanguage(language, { remember = false } = {}) {
  const available = document.querySelector(`[data-lang-content="${language}"]`);
  const resolved = available ? language : "en";
  document.querySelectorAll("[data-lang-content]").forEach((node) => {
    node.hidden = node.dataset.langContent !== resolved;
  });
  document.documentElement.lang = resolved === "zh" ? "zh-CN" : "en";
  const toggle = document.getElementById("lang-toggle");
  if (toggle) {
    const next = resolved === "zh" ? "en" : "zh";
    toggle.setAttribute("aria-pressed", String(resolved === "zh"));
    toggle.title = next === "zh" ? "Switch to Chinese (中文)" : "Switch to English";
    document.getElementById("lang-toggle-label").textContent = next === "zh" ? "中" : "EN";
  }
  if (!remember || resolved !== language) return;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, resolved);
  } catch (_) {
    // The page still switches even when preference storage is unavailable.
  }
}

const langToggle = document.getElementById("lang-toggle");
if (langToggle) {
  langToggle.addEventListener("click", () => {
    const current = document.documentElement.lang === "zh-CN" ? "zh" : "en";
    showLanguage(current === "zh" ? "en" : "zh", { remember: true });
  });
}
showLanguage(savedLanguage());

// Repository badge counts. Mirrors app.js's renderRepoBadges: same endpoints,
// same rule that counts are decoration, so a rate-limited API must never
// surface as an error state — the badges link out and stay usable blank.
const REPO_SLUG = "ktwu01/benchmark-radar";

const BADGE_ACTIONS = {
  "badge-stars": (count) => `Star this repository on GitHub. ${count} stars`,
  "badge-forks": (count) => `Fork this repository on GitHub. ${count} forks`,
  "badge-issues": (count) => `Open a new issue on GitHub. ${count} issues open`,
};

function setBadgeCount(id, value) {
  const badge = document.getElementById(id);
  const node = badge?.querySelector("[data-count]");
  if (!node) return;
  const count = Number(value || 0).toLocaleString();
  node.textContent = count;
  badge.setAttribute("aria-label", BADGE_ACTIONS[id](count));
}

async function renderRepoBadges() {
  try {
    const response = await fetch(`https://api.github.com/repos/${REPO_SLUG}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!response.ok) return;
    const repo = await response.json();
    setBadgeCount("badge-stars", repo.stargazers_count);
    setBadgeCount("badge-forks", repo.forks_count);
    // open_issues_count includes pull requests, so the issues badge asks the
    // search API for issues only, and stays blank if that fails rather than
    // showing the inflated number.
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
renderRepoBadges();

// The footer's share control, same behavior as the dashboard's.
const shareButton = document.getElementById("share-radar");
if (shareButton) {
  shareButton.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const shareData = {
      title: document.title,
      text: "Share Benchmark Radar",
      url: window.location.href,
    };
    try {
      if (navigator.share) await navigator.share(shareData);
      else await navigator.clipboard.writeText(shareData.url);
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = "Share";
      }, 1600);
    } catch (error) {
      if (error?.name !== "AbortError") console.error(error);
    }
  });
}

// The section nav scrolls horizontally on narrow screens, and Blog is its last
// item, so on a phone the reader lands on a brief with the active tab parked
// off the right edge. Nudging it into view keeps the "you are here" state
// visible; the dashboard needs no equivalent because its default view is the
// leftmost item.
const activeNav = document.querySelector('.view-nav [aria-current="page"]');
if (activeNav?.scrollIntoView) {
  activeNav.scrollIntoView({ block: "nearest", inline: "nearest" });
}
