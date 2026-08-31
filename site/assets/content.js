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

function showLanguage(language) {
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
  try {
    localStorage.setItem(LANG_STORAGE_KEY, resolved);
  } catch (_) {
    // The page still switches even when preference storage is unavailable.
  }
}

const toggle = document.getElementById("lang-toggle");
if (toggle) {
  toggle.addEventListener("click", () => showLanguage(toggle.dataset.nextLanguage || "zh"));
  showLanguage(savedLanguage());
}
