// Execute the real All dates deduplication helpers from app.js without
// copying their implementation into the test.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, "..", "site", "assets", "app.js"), "utf8");
const start = source.indexOf("function observationRecordKey(");
const end = source.indexOf("\nfunction populateSelect(", start);
if (start < 0 || end < 0) throw new Error("All dates deduplication helpers not found");

const harness = `${source.slice(start, end)}\nglobalThis.__latest = latestObservationsByRecord;`;
new Function(harness)();

const rows = [
  {
    observation_kind: "evidence",
    source: "GitHub Release",
    source_id: "modelscope/evalscope@v1.11.0",
    snapshot_date: "2026-08-25",
    total_score: 65.2,
  },
  {
    observation_kind: "evidence",
    source: "GitHub Release",
    source_id: "modelscope/evalscope@v1.11.0",
    snapshot_date: "2026-08-26",
    total_score: 55.15,
  },
  {
    observation_kind: "evidence",
    source: "GitHub",
    source_id: "modelscope/evalscope@v1.11.0",
    snapshot_date: "2026-08-25",
  },
  {
    observation_kind: "attention",
    observation_id: "hacker-news:123",
    source: "Hacker News",
    source_id: "123",
    snapshot_date: "2026-08-25",
  },
  {
    observation_kind: "attention",
    observation_id: "hacker-news:123",
    source: "Hacker News",
    source_id: "123",
    snapshot_date: "2026-08-26",
  },
  {
    observation_kind: "evidence",
    source: "arXiv",
    source_id: "2608.00001",
    snapshot_date: "2026-08-24",
  },
];

console.log(JSON.stringify(globalThis.__latest(rows)));
