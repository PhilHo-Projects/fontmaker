/* Specimen page. Font loading, parsing and uploading live in fontkit.js;
 * this file is only the panels. */

const $ = (s) => document.querySelector(s);
const el = FontKit.el;

const BODY = "Text is judged in the mass, not the specimen. A face that dazzles \
at ninety-six pixels can turn to mush at eleven, where the counters close, the \
joins clog, and the rhythm of stems either holds the line or falls apart. Set a \
paragraph, stand back, and squint: the grey should be even, the word spaces \
quiet, and nothing should jump out except what you meant to emphasise.";

const PAIRS = ["AV", "AW", "AY", "AT", "LT", "LY", "LV", "PA", "TA", "To",
  "Te", "Ta", "Ty", "Yo", "Ya", "Wa", "We", "Va", "Vo", "FA", "rn", "rt",
  "r.", "y,", "v.", "w.", "f)", "fi", "fl", "ff", "1/2", "?!", "—o", "“A”",
  "il", "1l", "0O", "8B", "5S", "2Z", "cl", "vv"];

const ROWS = [
  ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", 36],
  ["abcdefghijklmnopqrstuvwxyz", 36],
  ["0123456789", 36],
  [".,:;!?·'\"“”‘’ (){}[]/\\|-–—_", 26],
  ["&@#$£€¢¥%*+=<>~^§¶©®™°", 26],
  ["ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝŠŽ", 26],
  ["àáâãäåçèéêëìíîïñòóôõöùúûüýÿšž", 26],
  ["Hamburgefonstiv · handgloves", 26],
  ["0O1lI 8B5S2Z rn/m cl/d vv/w", 26],
  ["Sphinx of black quartz, judge my vow.", 26],
];

function panel(label, cls) {
  const p = el("div", "p " + (cls || ""));
  p.appendChild(el("span", "l", label));
  return p;
}

function line(text, px, extra) {
  const n = el("div", "s " + (extra || ""), text);
  if (px) n.style.fontSize = px + "px";
  return n;
}

function kv(pairs) {
  const t = el("table", "kv");
  pairs.forEach(([k, v]) => {
    const tr = el("tr");
    tr.appendChild(el("td", null, k));
    tr.appendChild(el("td", null, v == null || v === "" ? "—" : String(v)));
    t.appendChild(tr);
  });
  return t;
}

function render(info) {
  const host = $("#panels");
  host.textContent = "";
  const text = $("#text").value || " ";

  let p = panel("sample");
  const big = line(text, +$("#size").value, "sample");
  big.id = "big";
  p.appendChild(big);
  host.appendChild(p);

  p = panel("waterfall", "c6");
  const wf = el("div", "wf");
  [10, 12, 14, 16, 18, 21, 24, 30, 36, 48, 64].forEach((s) => {
    const row = el("div");
    row.appendChild(el("i", null, String(s)));
    row.appendChild(line(text, s));
    wf.appendChild(row);
  });
  p.appendChild(wf);
  host.appendChild(p);

  p = panel("characters", "c6");
  const rows = el("div", "rows");
  ROWS.forEach(([s, px]) => rows.appendChild(line(s, px)));
  p.appendChild(rows);
  host.appendChild(p);

  p = panel("paragraph 16 / 13 / 11", "c8");
  [16, 13, 11].forEach((s) => {
    const n = line(BODY, s, "para");
    n.style.marginBottom = "8px";
    p.appendChild(n);
  });
  host.appendChild(p);

  p = panel("pairs", "c4");
  const pr = el("div", "pairs");
  PAIRS.forEach((s) => pr.appendChild(line(s, 30)));
  p.appendChild(pr);
  host.appendChild(p);

  const chars = (info && info.chars) || [];
  p = panel("glyphs (" + chars.length + " mapped)");
  const grid = el("div", "gl s");
  chars.forEach((c) => {
    if (c < 0x21) return;
    const s = el("span", null, String.fromCodePoint(c));
    s.title = "U+" + c.toString(16).toUpperCase().padStart(4, "0");
    grid.appendChild(s);
  });
  p.appendChild(grid);
  host.appendChild(p);

  const upm = (info && info.upm) || 1000;
  const pct = (v) => (v == null ? "—" : v + "  (" + Math.round(v / upm * 100) + "%)");
  p = panel("metrics", "c4");
  p.appendChild(kv([
    ["units/em", info.upm], ["glyphs", info.numGlyphs],
    ["cap height", pct(info.capHeight)], ["x-height", pct(info.xHeight)],
    ["ascender", info.ascender], ["descender", info.descender],
    ["line gap", info.lineGap],
    ["bbox", info.bbox ? info.bbox.join(" ") : "—"],
  ]));
  host.appendChild(p);

  p = panel("names", "c4");
  p.appendChild(kv([
    ["family", info.names.typoFamily || info.names.family],
    ["style", info.names.style], ["version", info.names.version],
    ["weight", info.weightClass], ["vendor", info.vendor],
    ["typo asc", info.typoAscender], ["typo desc", info.typoDescender],
    ["win asc/desc", info.winAscent != null
      ? info.winAscent + " / " + info.winDescent : "—"],
  ]));
  host.appendChild(p);

  p = panel("figures", "c4");
  p.appendChild(line("0123456789", 34));
  p.appendChild(line("$1,234.56  £987  €0.50", 20));
  p.appendChild(line("2026-07-27  09:41  ¾  №12", 20));
  p.appendChild(line("(01) 234–567  #48  50%", 20));
  host.appendChild(p);

  applyTracking();
}

function applyTracking() {
  const t = $("#track").value;
  document.querySelectorAll(".s").forEach((n) => {
    n.style.letterSpacing = (t / 1000) + "em";
  });
}

$("#text").addEventListener("input", () => {
  if (FontKit.state.active && FontKit.state.active.buf)
    render(FontKit.parseFont(FontKit.state.active.buf));
});

$("#size").addEventListener("input", () => {
  $("#sizeout").value = $("#size").value;
  const b = $("#big");
  if (b) b.style.fontSize = $("#size").value + "px";
});

$("#track").addEventListener("input", () => {
  $("#trackout").value = $("#track").value;
  applyTracking();
});

$("#sizeout").value = $("#size").value;
$("#trackout").value = $("#track").value;

FontKit.wire({
  select: $("#font"),
  upload: $("#upload"),
  download: $("#download"),
  theme: $("#theme"),
  drop: $("#drop"),
  status: $("#status"),
  onchange: (entry, info) => render(info),
});
