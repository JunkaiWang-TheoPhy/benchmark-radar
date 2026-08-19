// The logo audit page (issue #261).
//
// Three brand marks shipped wrong and stayed wrong: "Google DeepMind" was
// keyed to simple-icons' Google "G", GPT fell through to a hand-drawn rosette,
// and Meta's path was genuine for 395 characters and invented after that. None
// were caught, because nothing on the site showed the marks side by side at a
// size where a malformed path is visible.
//
// This page is that surface. It imports the real resolvers rather than
// reimplementing them, so it cannot report a mark the charts do not draw.
import {
  ORGANIZATION_ICONS,
  ORGANIZATION_FALLBACK_ICON,
  MODEL_FAMILY_ICONS,
  organizationColor,
  organizationIcon,
  modelIcon,
  iconGlyph,
} from "./glyphs.js";

const byId = (id) => document.getElementById(id);

// Which named table a resolved path came from, for the provenance line. Marks
// are compared by identity of the path string: two organizations sharing a
// path is itself something the reviewer should see.
function iconSource(paths) {
  if (paths.length === 1 && paths[0] === ORGANIZATION_FALLBACK_ICON) {
    return { label: "generic spark (no brand mark)", fallback: true };
  }
  for (const [name, value] of Object.entries(MODEL_FAMILY_ICONS)) {
    if (value === paths) return { label: `MODEL_FAMILY_ICONS.${name}`, fallback: false };
  }
  for (const [name, value] of Object.entries(ORGANIZATION_ICONS)) {
    if (value === paths) return { label: `ORGANIZATION_ICONS[${name}]`, fallback: false };
  }
  return { label: "unknown table", fallback: false };
}

// A path whose drawn extent escapes the 24-unit viewBox is malformed: every
// mark in both source sets is authored to fit it. This is what makes a
// fabricated path (Meta, before the fix) visible mechanically rather than
// relying on the reviewer to notice a blob.
function suspectGeometry(paths) {
  const probe = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  probe.setAttribute("viewBox", "0 0 24 24");
  probe.style.cssText = "position:absolute;width:24px;height:24px;left:-9999px;top:0";
  for (const d of paths) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    probe.append(path);
  }
  document.body.append(probe);
  let bad = false;
  try {
    const box = probe.getBBox();
    const slack = 0.75;
    bad =
      box.x < -slack ||
      box.y < -slack ||
      box.x + box.width > 24 + slack ||
      box.y + box.height > 24 + slack;
  } catch (_) {
    bad = true;
  }
  probe.remove();
  return bad;
}

function glyphSvg(paths, color, size, px) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", px);
  svg.setAttribute("height", px);
  svg.setAttribute("aria-hidden", "true");
  svg.append(iconGlyph(paths, 12, 12, size, "logos-glyph", color));
  return svg;
}

// The mark exactly as a chart draws it: a 9-unit pale face with the glyph at
// 14 units over it. Shown at real scale so "is this legible at chart size?" is
// answerable here rather than only on the chart.
function chartMark(paths, color) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 32 32");
  svg.setAttribute("width", 32);
  svg.setAttribute("height", 32);
  svg.setAttribute("aria-hidden", "true");
  const face = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  face.setAttribute("cx", 16);
  face.setAttribute("cy", 16);
  face.setAttribute("r", 9);
  face.setAttribute("class", "logos-chart-face");
  svg.append(face);
  svg.append(iconGlyph(paths, 16, 16, 14, "logos-glyph", color));
  return svg;
}

function card({ id, paths, color, name, sub, layer }) {
  const source = iconSource(paths);
  const suspect = suspectGeometry(paths);

  const node = document.createElement("article");
  node.className = "logos-card";
  node.id = id;
  node.dataset.fallback = String(source.fallback);
  node.dataset.suspect = String(suspect);
  if (layer) node.dataset.layer = layer;

  const head = document.createElement("div");
  head.className = "logos-card-head";
  const badge = document.createElement("a");
  badge.className = "logos-id";
  badge.href = `#${id}`;
  badge.textContent = id;
  head.append(badge);

  const chips = document.createElement("span");
  chips.className = "logos-chips";
  if (source.fallback) {
    const chip = document.createElement("span");
    chip.className = "chip chip-fallback";
    chip.textContent = "no mark";
    chips.append(chip);
  }
  if (suspect) {
    const chip = document.createElement("span");
    chip.className = "chip chip-suspect";
    chip.textContent = "suspect";
    chips.append(chip);
  }
  if (layer) {
    const chip = document.createElement("span");
    chip.className = `chip chip-layer chip-layer-${layer}`;
    chip.textContent = layer;
    chips.append(chip);
  }
  head.append(chips);
  node.append(head);

  const art = document.createElement("div");
  art.className = "logos-art";
  art.style.setProperty("--org-color", color);
  const big = document.createElement("div");
  big.className = "logos-big";
  big.append(glyphSvg(paths, color, 24, 96));
  const small = document.createElement("div");
  small.className = "logos-small";
  small.append(chartMark(paths, color));
  const smallLabel = document.createElement("span");
  smallLabel.className = "logos-small-label";
  smallLabel.textContent = "chart size";
  small.append(smallLabel);
  art.append(big, small);
  node.append(art);

  const body = document.createElement("div");
  body.className = "logos-body";
  const title = document.createElement("h3");
  title.textContent = name;
  body.append(title);
  if (sub) {
    const p = document.createElement("p");
    p.className = "logos-sub";
    p.textContent = sub;
    body.append(p);
  }
  const prov = document.createElement("p");
  prov.className = "logos-prov";
  prov.textContent = source.label;
  body.append(prov);
  const swatch = document.createElement("p");
  swatch.className = "logos-swatch-line";
  const dot = document.createElement("span");
  dot.className = "logos-swatch";
  dot.style.background = color;
  swatch.append(dot, document.createTextNode(color));
  body.append(swatch);
  node.append(body);
  return node;
}

async function main() {
  const registry = await (await fetch("data/logo-registry.json")).json();

  const orgHost = byId("logos-organizations");
  for (const [name, id] of Object.entries(registry.organizations)) {
    orgHost.append(
      card({ id, paths: organizationIcon(name), color: organizationColor(name), name }),
    );
  }

  // Every model that draws a point, from both layers. A crawled model and a
  // curated one resolve their mark through the same modelIcon call, so both
  // belong here -- but the layer is printed on the card, because a crawled row
  // carries no protocol and no evaluation date and must not read as a curated
  // one's equal (issue #268).
  const modelHost = byId("logos-models");
  const layers = registry.model_layers || {};
  for (const [key, id] of Object.entries(registry.models)) {
    const [model, organization] = key.split("␟");
    modelHost.append(
      card({
        id,
        paths: modelIcon(model, organization),
        color: organizationColor(organization),
        name: model,
        sub: organization,
        layer: layers[key],
      }),
    );
  }

  const cards = [...document.querySelectorAll(".logos-card")];
  const fallback = cards.filter((c) => c.dataset.fallback === "true").length;
  const suspect = cards.filter((c) => c.dataset.suspect === "true").length;
  byId("logos-status").textContent =
    `${cards.length} marks · ${fallback} without a brand mark · ${suspect} with suspect geometry`;

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-filter]").forEach((b) => b.classList.remove("is-active"));
      button.classList.add("is-active");
      const mode = button.dataset.filter;
      for (const node of cards) {
        node.hidden =
          mode === "fallback"
            ? node.dataset.fallback !== "true"
            : mode === "suspect"
              ? node.dataset.suspect !== "true"
              : mode === "curated" || mode === "crawled"
                ? node.dataset.layer !== mode
                : false;
      }
    });
  });
}

main();
