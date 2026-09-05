// Executes site/assets/blog.js in a controlled DOM environment to test
// client-side language switching and i18n behavior for translated vs
// untranslated blog posts, and verifies error handling on malformed i18n payloads.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const blogJsSource = readFileSync(join(here, "..", "site", "assets", "blog.js"), "utf8");

const mode = process.argv[2] || "untranslated"; // "untranslated" | "translated" | "malformed-json"
const targetLang = process.argv[3] || "zh"; // "zh" | "en"
const remember = process.argv[4] === "remember";

class MockNode {
  constructor(tag, id = "") {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.attributes = {};
    this.classList = {
      _classes: new Set(),
      add: (...cls) => cls.forEach((c) => this.classList._classes.add(c)),
      contains: (cls) => this.classList._classes.has(cls),
      remove: (...cls) => cls.forEach((c) => this.classList._classes.delete(c)),
    };
    this.dataset = {};
    this._text = "";
    this.hidden = false;
    this.children = [];
    this.listeners = {};
  }
  get textContent() {
    return this._text;
  }
  set textContent(val) {
    this._text = String(val);
  }
  getAttribute(name) {
    return this.attributes[name] ?? null;
  }
  setAttribute(name, val) {
    this.attributes[name] = String(val);
    if (name.startsWith("data-")) {
      const prop = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      this.dataset[prop] = String(val);
    }
  }
  removeAttribute(name) {
    delete this.attributes[name];
  }
  hasAttribute(name) {
    return name in this.attributes;
  }
  addEventListener(event, handler) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(handler);
  }
  click() {
    const list = this.listeners["click"] || [];
    list.forEach((cb) => cb({ currentTarget: this }));
  }
}

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, val) => storage.set(key, String(val)),
};

const consoleErrors = [];
const originalConsoleError = console.error;
console.error = (...args) => {
  consoleErrors.push(args.map(String).join(" "));
};

const docElement = new MockNode("html");
docElement.lang = "en";

// Elements
const bakedI18n = new MockNode("script", "chrome-i18n");
if (mode === "malformed-json") {
  bakedI18n.textContent = "{invalid: json,";
} else {
  bakedI18n.textContent = JSON.stringify({
    Contact: "联系作者",
    "Switch to English": "切换到英文",
    "Switch to Chinese (中文)": "Switch to Chinese (中文)",
    "Star this repository on GitHub. {count} stars": "在 GitHub 上给这个仓库点 Star。{count} 个 star",
    Blog: "博客",
  });
}

const langToggle = new MockNode("button", "lang-toggle");
langToggle.setAttribute("aria-pressed", "false");
langToggle.setAttribute("title", "Switch to Chinese (中文)");
const langToggleLabel = new MockNode("span", "lang-toggle-label");
langToggleLabel.textContent = "中";

const navContact = new MockNode("a");
navContact.setAttribute("data-i18n", "Contact");
navContact.textContent = "Contact";

const enContent = new MockNode("div");
enContent.dataset.langContent = "en";
enContent.textContent = "English body content";
enContent.hidden = false;

let zhContent = null;
if (mode === "translated") {
  zhContent = new MockNode("div");
  zhContent.dataset.langContent = "zh";
  zhContent.textContent = "中文正文内容";
  zhContent.hidden = true;
}

const allNodes = [bakedI18n, langToggle, langToggleLabel, navContact, enContent];
if (zhContent) allNodes.push(zhContent);

globalThis.document = {
  documentElement: docElement,
  getElementById: (id) => {
    if (id === "chrome-i18n") return bakedI18n;
    if (id === "lang-toggle") return langToggle;
    if (id === "lang-toggle-label") return langToggleLabel;
    return null;
  },
  querySelectorAll: (selector) => {
    if (selector === "[data-lang-content]") {
      return zhContent ? [enContent, zhContent] : [enContent];
    }
    if (selector === "[data-i18n]") return [navContact];
    if (selector === "[data-i18n-title]") return [];
    if (selector === "[data-i18n-aria]") return [];
    if (selector === '.view-nav [aria-current="page"]') return [];
    return [];
  },
  querySelector: (selector) => {
    if (selector === '[data-lang-content="zh"]') return zhContent;
    if (selector === '[data-lang-content="en"]') return enContent;
    if (selector === '.view-nav [aria-current="page"]') return null;
    return null;
  },
};

globalThis.window = {
  location: { search: "", href: "http://localhost:8734/blog/test/" },
};

// blog.js fetches GitHub badge counts on load. Keep the harness offline and
// deterministic: never hit the network, and never reject so language tests
// are not coupled to badge rendering.
globalThis.fetch = async () => ({ ok: false, json: async () => ({}) });

// Evaluate blog.js in this sandbox
new Function(blogJsSource)();

// Now perform the language switch
if (targetLang) {
  // Can trigger either by clicking toggle or by calling showLanguage directly
  langToggle.click();
  // If the toggle flip didn't match targetLang (e.g. if targetLang was 'en' and initial was 'en'):
  const currentLang = docElement.lang === "zh-CN" ? "zh" : "en";
  if (currentLang !== targetLang) {
    langToggle.click();
  }
}

const result = {
  mode,
  targetLang,
  htmlLang: docElement.lang,
  enHidden: enContent.hidden,
  zhHidden: zhContent ? zhContent.hidden : null,
  toggleAriaPressed: langToggle.getAttribute("aria-pressed"),
  toggleLabel: langToggleLabel.textContent,
  toggleTooltip: langToggle.getAttribute("data-tooltip"),
  toggleTitle: langToggle.getAttribute("title"),
  storedLang: storage.get("benchmark-radar:lang") ?? null,
  contactText: navContact.textContent,
  consoleErrors,
};

process.stdout.write(JSON.stringify(result));
