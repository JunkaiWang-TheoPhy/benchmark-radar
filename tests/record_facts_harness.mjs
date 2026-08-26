// Execute the real metadata helpers from app.js so the test proves missing
// versus zero behavior rather than matching implementation source strings.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, "..", "site", "assets", "app.js"), "utf8");
const start = source.indexOf("const RECORD_METRIC_LABELS");
const end = source.indexOf("\nfunction safeHttpUrl", start);
if (start < 0 || end < 0) throw new Error("Record metadata helpers not found");

globalThis.t = (value) => value;
globalThis.getLang = () => "en";
globalThis.formatDate = (value) => `date:${value}`;
globalThis.document = { createTextNode: (text) => ({ text }) };
globalThis.element = (tag, props = {}, children = []) => ({ tag, props, children });
const harness = `${source.slice(start, end)}
globalThis.__recordFactEntries = recordFactEntries;
globalThis.__recordDateEntries = recordDateEntries;
globalThis.__recordFacts = recordFacts;`;
new Function(harness)();

const reportedItem = {
  organizations: ["OpenAI"],
  authors: ["Alice", "Bob", "Carol"],
  metrics: { stars: 0, forks: null },
};
const reported = globalThis.__recordFactEntries(reportedItem);
const unreported = globalThis.__recordFactEntries({
  authors: ["Deyao Hong"],
  metrics: {},
});
const dates = globalThis.__recordDateEntries({
  published_at: "2026-08-24T17:59:04Z",
  updated_at: "2026-08-25T17:59:04Z",
});
const rendered = globalThis.__recordFacts(reportedItem);

console.log(
  JSON.stringify({
    reported,
    unreported,
    dates,
    rendered: {
      tag: rendered.tag,
      className: rendered.props.className,
      role: rendered.props.attrs.role,
      ariaLabel: rendered.props.attrs["aria-label"],
    },
  }),
);
