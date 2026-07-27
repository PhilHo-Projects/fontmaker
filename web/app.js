/* fontmaker specimen page.
 *
 * Works two ways with no configuration: served by web/server.py it lists and
 * uploads fonts; opened as a plain file:// it falls back to whatever you drop
 * on it. Every font is fetched as bytes once and used for both the @font-face
 * and the metrics readout, so the numbers on screen come from the file rather
 * than from what the CSS happened to do.
 */

const $ = (s) => document.querySelector(s);
const el = (tag, cls, txt) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
};

const state = {
  fonts: [],          // {file, name, size, url?, buf?}
  active: null,
  face: null,
  readOnly: false,
  server: false,
};

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

/* ------------------------------------------------------------------ sfnt */

function parseFont(buf) {
  const d = new DataView(buf);
  const u8 = (o) => d.getUint8(o);
  const u16 = (o) => d.getUint16(o);
  const i16 = (o) => d.getInt16(o);
  const u32 = (o) => d.getUint32(o);

  const out = { tables: {}, names: {}, chars: [] };
  if (buf.byteLength < 12) return out;

  let base = 0;
  if (u32(0) === 0x74746366) base = u32(12);           // 'ttcf': first font
  const numTables = u16(base + 4);
  for (let i = 0; i < numTables; i++) {
    const r = base + 12 + 16 * i;
    if (r + 16 > buf.byteLength) break;
    const tag = String.fromCharCode(u8(r), u8(r + 1), u8(r + 2), u8(r + 3));
    out.tables[tag] = { off: u32(r + 8), len: u32(r + 12) };
  }
  const T = (t) => out.tables[t] && out.tables[t].off;

  const head = T("head");
  if (head) {
    out.upm = u16(head + 18);
    out.bbox = [i16(head + 36), i16(head + 38), i16(head + 40), i16(head + 42)];
  }
  const hhea = T("hhea");
  if (hhea) {
    out.ascender = i16(hhea + 4);
    out.descender = i16(hhea + 6);
    out.lineGap = i16(hhea + 8);
  }
  const maxp = T("maxp");
  if (maxp) out.numGlyphs = u16(maxp + 4);

  const os2 = T("OS/2");
  if (os2) {
    const ver = u16(os2);
    out.weightClass = u16(os2 + 4);
    out.vendor = String.fromCharCode(u8(os2 + 58), u8(os2 + 59),
      u8(os2 + 60), u8(os2 + 61)).trim();
    out.typoAscender = i16(os2 + 68);
    out.typoDescender = i16(os2 + 70);
    out.typoLineGap = i16(os2 + 72);
    out.winAscent = u16(os2 + 74);
    out.winDescent = u16(os2 + 76);
    if (ver >= 2) {
      out.xHeight = i16(os2 + 86);
      out.capHeight = i16(os2 + 88);
    }
  }

  const name = T("name");
  if (name) {
    const count = u16(name + 2);
    const strOff = name + u16(name + 4);
    const want = { 1: "family", 2: "style", 5: "version", 16: "typoFamily" };
    for (let i = 0; i < count; i++) {
      const r = name + 6 + 12 * i;
      const plat = u16(r), nid = u16(r + 6);
      const len = u16(r + 8), off = strOff + u16(r + 10);
      const key = want[nid];
      if (!key || off + len > buf.byteLength) continue;
      let s = "";
      if (plat === 3) {
        for (let j = 0; j + 1 < len; j += 2) s += String.fromCharCode(u16(off + j));
      } else {
        for (let j = 0; j < len; j++) s += String.fromCharCode(u8(off + j));
      }
      if (s && (!out.names[key] || plat === 3)) out.names[key] = s;
    }
  }

  const cmap = T("cmap");
  if (cmap) out.chars = readCmap(d, cmap, buf.byteLength);
  return out;
}

function readCmap(d, cmap, size) {
  const u16 = (o) => d.getUint16(o), u32 = (o) => d.getUint32(o);
  const n = u16(cmap + 2);
  let best = 0, bestScore = -1;
  for (let i = 0; i < n; i++) {
    const r = cmap + 4 + 8 * i;
    const plat = u16(r), enc = u16(r + 2), off = cmap + u32(r + 4);
    if (off + 4 > size) continue;
    // prefer full-repertoire Unicode, then BMP
    const score = (plat === 3 && enc === 10) ? 4 : (plat === 0 && enc >= 4) ? 3
      : (plat === 3 && enc === 1) ? 2 : (plat === 0) ? 1 : 0;
    if (score > bestScore) { bestScore = score; best = off; }
  }
  if (!best) return [];

  const chars = [];
  const fmt = u16(best);
  const LIMIT = 8000;
  if (fmt === 4) {
    const segX2 = u16(best + 6), seg = segX2 / 2;
    const ends = best + 14, starts = ends + segX2 + 2;
    const deltas = starts + segX2, ranges = deltas + segX2;
    for (let s = 0; s < seg && chars.length < LIMIT; s++) {
      const end = u16(ends + s * 2), start = u16(starts + s * 2);
      const delta = d.getInt16(deltas + s * 2), ro = u16(ranges + s * 2);
      for (let c = start; c <= end && c !== 0xFFFF && chars.length < LIMIT; c++) {
        let g;
        if (ro === 0) {
          g = (c + delta) & 0xFFFF;
        } else {
          const gi = ranges + s * 2 + ro + (c - start) * 2;
          if (gi + 1 >= size) continue;
          g = u16(gi);
          if (g) g = (g + delta) & 0xFFFF;
        }
        if (g) chars.push(c);
      }
    }
  } else if (fmt === 12) {
    const groups = u32(best + 12);
    for (let i = 0; i < groups && chars.length < LIMIT; i++) {
      const r = best + 16 + 12 * i;
      if (r + 12 > size) break;
      const a = u32(r), b = u32(r + 4);
      for (let c = a; c <= b && chars.length < LIMIT; c++) chars.push(c);
    }
  } else if (fmt === 6) {
    const first = u16(best + 6), cnt = u16(best + 8);
    for (let i = 0; i < cnt; i++) if (u16(best + 10 + i * 2)) chars.push(first + i);
  }
  return chars;
}

/* ---------------------------------------------------------------- panels */

function panel(label, cls) {
  const p = el("div", "p " + (cls || ""));
  p.appendChild(el("span", "l", label));
  return p;
}

function specimenLine(text, px, extra) {
  const n = el("div", "s " + (extra || ""), text);
  if (px) n.style.fontSize = px + "px";
  return n;
}

function render(info) {
  const host = $("#panels");
  host.textContent = "";
  const text = $("#text").value || " ";

  // sample -------------------------------------------------------------
  let p = panel("sample");
  const big = specimenLine(text, +$("#size").value, "sample");
  big.id = "big";
  p.appendChild(big);
  host.appendChild(p);

  // waterfall ----------------------------------------------------------
  p = panel("waterfall", "c6");
  const wf = el("div", "wf");
  [10, 12, 14, 16, 18, 21, 24, 30, 36, 48, 64].forEach((s) => {
    const row = el("div");
    row.appendChild(el("i", null, String(s)));
    row.appendChild(specimenLine(text, s));
    wf.appendChild(row);
  });
  p.appendChild(wf);
  host.appendChild(p);

  // character rows -----------------------------------------------------
  p = panel("characters", "c6");
  const rows = el("div", "rows");
  ROWS.forEach(([s, px]) => rows.appendChild(specimenLine(s, px)));
  p.appendChild(rows);
  host.appendChild(p);

  // paragraphs ---------------------------------------------------------
  p = panel("paragraph 16 / 13 / 11", "c8");
  [16, 13, 11].forEach((s) => {
    const n = specimenLine(BODY, s, "para");
    n.style.marginBottom = "8px";
    p.appendChild(n);
  });
  host.appendChild(p);

  // pairs --------------------------------------------------------------
  p = panel("pairs", "c4");
  const pr = el("div", "pairs");
  PAIRS.forEach((s) => pr.appendChild(specimenLine(s, 30)));
  p.appendChild(pr);
  host.appendChild(p);

  // reversed / tinted --------------------------------------------------
  p = panel("reversed", "c6 inv");
  p.appendChild(specimenLine(text, 44));
  p.appendChild(specimenLine(BODY.slice(0, 150), 13, "para"));
  host.appendChild(p);

  p = panel("tinted", "c6 tint");
  p.appendChild(specimenLine(text, 44));
  p.appendChild(specimenLine(BODY.slice(0, 150), 13, "para"));
  host.appendChild(p);

  // glyph grid ---------------------------------------------------------
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

  // readouts -----------------------------------------------------------
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
  p.appendChild(specimenLine("0123456789", 34));
  p.appendChild(specimenLine("1234567890", 20));
  p.appendChild(specimenLine("$1,234.56  £987  €0.50", 20));
  p.appendChild(specimenLine("2026-07-27  09:41", 20));
  host.appendChild(p);

  applyTracking();
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

function applyTracking() {
  const t = $("#track").value;
  document.querySelectorAll(".s").forEach((n) => {
    n.style.letterSpacing = (t / 1000) + "em";
  });
}

/* ----------------------------------------------------------------- fonts */

async function activate(entry) {
  status("loading " + entry.name);
  try {
    let buf = entry.buf;
    if (!buf) {
      const res = await fetch(entry.url, { cache: "no-cache" });
      if (!res.ok) throw new Error(res.status + " " + res.statusText);
      buf = await res.arrayBuffer();
      entry.buf = buf;
    }
    if (state.face) document.fonts.delete(state.face);
    const face = new FontFace("Specimen", buf);
    await face.load();
    document.fonts.add(face);
    state.face = face;
    state.active = entry;
    render(parseFont(buf));
    status(entry.file + " · " + Math.round(buf.byteLength / 1024) + " kB");
  } catch (e) {
    status("failed: " + e.message, true);
  }
}

function status(msg, isErr) {
  const s = $("#status");
  s.textContent = msg;
  s.className = isErr ? "err" : "";
}

function fillSelect() {
  const sel = $("#font");
  sel.textContent = "";
  state.fonts.forEach((f, i) => {
    const o = el("option", null, f.name);
    o.value = String(i);
    sel.appendChild(o);
  });
  sel.disabled = !state.fonts.length;
}

async function loadList() {
  try {
    const res = await fetch("api/fonts", { cache: "no-cache" });
    if (!res.ok) throw new Error("no api");
    const data = await res.json();
    state.server = true;
    state.readOnly = !!data.readOnly;
    state.fonts = data.fonts.map((f) => ({
      file: f.file, name: f.name, size: f.size, url: "fonts/" + encodeURIComponent(f.file),
    }));
    fillSelect();
    if (state.fonts.length) {
      $("#font").value = "0";
      await activate(state.fonts[0]);
    } else {
      status("no fonts on the server — upload one");
    }
  } catch (e) {
    state.server = false;
    fillSelect();
    status("offline — drop a .ttf to preview");
  }
}

async function addLocal(files) {
  for (const file of files) {
    if (!/\.(ttf|otf)$/i.test(file.name)) continue;
    const buf = await file.arrayBuffer();
    let entry = { file: file.name, name: file.name.replace(/\.[^.]+$/, ""), buf };

    if (state.server && !state.readOnly) {
      try {
        const res = await fetch("api/fonts?name=" + encodeURIComponent(file.name), {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream" },
          body: buf,
        });
        if (!res.ok) {
          const j = await res.json().catch(() => ({}));
          status("upload failed: " + (j.error || res.status), true);
        } else {
          entry.url = "fonts/" + encodeURIComponent(file.name);
        }
      } catch (e) {
        status("upload failed: " + e.message, true);
      }
    }

    const at = state.fonts.findIndex((f) => f.file === entry.file);
    if (at >= 0) state.fonts[at] = entry; else state.fonts.push(entry);
  }
  state.fonts.sort((a, b) => a.name.localeCompare(b.name));
  fillSelect();
  const last = state.fonts.findIndex((f) => f.buf);
  if (last >= 0) {
    $("#font").value = String(last);
    await activate(state.fonts[last]);
  }
}

/* ------------------------------------------------------------------ wire */

$("#font").addEventListener("change", (e) => {
  const f = state.fonts[+e.target.value];
  if (f) activate(f);
});

$("#upload").addEventListener("change", (e) => {
  addLocal(e.target.files);
  e.target.value = "";
});

$("#text").addEventListener("input", () => {
  const t = $("#text").value || " ";
  document.querySelectorAll("#big").forEach((n) => { n.textContent = t; });
  if (state.active && state.active.buf) render(parseFont(state.active.buf));
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

$("#theme").addEventListener("click", () => {
  const now = document.documentElement.getAttribute("data-theme") === "light";
  document.documentElement.setAttribute("data-theme", now ? "dark" : "light");
  try { localStorage.setItem("fm-theme", now ? "dark" : "light"); } catch (e) { /* private mode */ }
});

["dragenter", "dragover"].forEach((ev) =>
  document.addEventListener(ev, (e) => { e.preventDefault(); $("#drop").classList.add("on"); }));
["dragleave", "drop"].forEach((ev) =>
  document.addEventListener(ev, (e) => {
    e.preventDefault();
    if (ev === "dragleave" && e.relatedTarget) return;
    $("#drop").classList.remove("on");
  }));
document.addEventListener("drop", (e) => {
  if (e.dataTransfer && e.dataTransfer.files.length) addLocal(e.dataTransfer.files);
});

try {
  const saved = localStorage.getItem("fm-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) { /* private mode */ }

$("#sizeout").value = $("#size").value;
loadList();
