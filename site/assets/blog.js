// Language switch for the generated blog pages.
//
// Each brief ships both language versions in the document when the snapshot
// stored a reviewed Chinese translation, so switching is a visibility change
// and never a fetch. Pages without a stored translation ship no toggle at all:
// a control that switches to identical text is broken, and translating here
// would publish text nobody reviewed.
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
    toggle.dataset.nextLanguage = next;
    toggle.setAttribute("aria-pressed", String(resolved === "zh"));
    toggle.setAttribute(
      "aria-label",
      next === "zh" ? "Switch to Chinese (中文)" : "Switch to English",
    );
    document.getElementById("lang-toggle-label").textContent = next === "zh" ? "中" : "EN";
  }
  if (!remember || resolved !== language) return;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, resolved);
  } catch (_) {
    // The page still switches even when preference storage is unavailable.
  }
}

const toggle = document.getElementById("lang-toggle");
if (toggle) {
  toggle.addEventListener("click", () =>
    showLanguage(toggle.dataset.nextLanguage || "zh", { remember: true }),
  );
}
showLanguage(savedLanguage());

// The section nav scrolls horizontally on narrow screens, and Blog is its last
// item, so on a phone the reader lands on a brief with the active tab parked
// off the right edge. Nudging it into view keeps the "you are here" state
// visible; the dashboard needs no equivalent because its default view is the
// leftmost item.
const activeNav = document.querySelector('.view-nav [aria-current="page"]');
if (activeNav?.scrollIntoView) {
  activeNav.scrollIntoView({ block: "nearest", inline: "nearest" });
}
