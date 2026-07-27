/* Shared by both pages: the font list, loading a face, parsing it, uploading,
 * and the bits of chrome that behave the same everywhere.
 *
 * Every font is fetched as bytes once and used for both the @font-face and the
 * metrics readout, so the numbers on screen come from the file rather than
 * from what the CSS happened to do. The active font is remembered across
 * pages, which is the only reason the two-page split is bearable.
 */

const FontKit = (() => {
  const state = {
    fonts: [],        // {file, name, size, url?, buf?}
    active: null,
    face: null,
    server: false,
    readOnly: false,
  };

  const REMEMBER = "fm-font";
  let onchange = () => {};
  let statusEl = null;

  const el = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  };

  function status(msg, isErr) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = isErr ? "err" : "";
  }

  /* ---------------------------------------------------------------- sfnt */

  function parseFont(buf) {
    const d = new DataView(buf);
    const u8 = (o) => d.getUint8(o);
    const u16 = (o) => d.getUint16(o);
    const i16 = (o) => d.getInt16(o);
    const u32 = (o) => d.getUint32(o);

    const out = { tables: {}, names: {}, chars: [] };
    if (buf.byteLength < 12) return out;

    let base = 0;
    if (u32(0) === 0x74746366) base = u32(12);        // 'ttcf': first font
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

  /* --------------------------------------------------------------- fonts */

  async function activate(entry) {
    if (!entry) return;
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
      try { localStorage.setItem(REMEMBER, entry.file); } catch (e) { /* private */ }
      onchange(entry, parseFont(buf));
      status(entry.file + " · " + Math.round(buf.byteLength / 1024) + " kB");
    } catch (e) {
      status("failed: " + e.message, true);
    }
  }

  function fillSelect(sel) {
    if (!sel) return;
    sel.textContent = "";
    state.fonts.forEach((f, i) => {
      const o = el("option", null, f.name);
      o.value = String(i);
      sel.appendChild(o);
    });
    sel.disabled = !state.fonts.length;
    const at = state.fonts.indexOf(state.active);
    if (at >= 0) sel.value = String(at);
  }

  async function loadList(sel) {
    let want = null;
    try { want = localStorage.getItem(REMEMBER); } catch (e) { /* private */ }
    try {
      const res = await fetch("api/fonts", { cache: "no-cache" });
      if (!res.ok) throw new Error("no api");
      const data = await res.json();
      state.server = true;
      state.readOnly = !!data.readOnly;
      state.fonts = data.fonts.map((f) => ({
        file: f.file, name: f.name, size: f.size,
        url: "fonts/" + encodeURIComponent(f.file),
      }));
      const pick = state.fonts.find((f) => f.file === want) || state.fonts[0];
      state.active = pick;
      fillSelect(sel);
      if (pick) await activate(pick);
      else status("no fonts on the server — upload one");
    } catch (e) {
      state.server = false;
      fillSelect(sel);
      status("offline — drop a .ttf to preview");
    }
  }

  async function addLocal(files, sel) {
    let newest = null;
    for (const file of files) {
      if (!/\.(ttf|otf)$/i.test(file.name)) continue;
      const buf = await file.arrayBuffer();
      const entry = {
        file: file.name, name: file.name.replace(/\.[^.]+$/, ""), buf,
      };
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
      newest = entry;
    }
    state.fonts.sort((a, b) => a.name.localeCompare(b.name));
    if (newest) {
      state.active = newest;
      fillSelect(sel);
      await activate(newest);
    } else {
      fillSelect(sel);
    }
  }

  function download() {
    const a = state.active;
    if (!a || !a.buf) return;
    const url = URL.createObjectURL(new Blob([a.buf], { type: "font/ttf" }));
    const link = el("a");
    link.href = url;
    link.download = a.file;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* --------------------------------------------------------------- chrome */

  function wire(opts) {
    statusEl = opts.status || null;
    onchange = opts.onchange || (() => {});

    if (opts.select) {
      opts.select.addEventListener("change", (e) =>
        activate(state.fonts[+e.target.value]));
    }
    if (opts.upload) {
      opts.upload.addEventListener("change", (e) => {
        addLocal(e.target.files, opts.select);
        e.target.value = "";
      });
    }
    if (opts.download) opts.download.addEventListener("click", download);

    if (opts.theme) {
      opts.theme.addEventListener("click", () => {
        const light = document.documentElement.getAttribute("data-theme") === "light";
        const next = light ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", next);
        try { localStorage.setItem("fm-theme", next); } catch (e) { /* private */ }
      });
    }

    if (opts.drop) {
      ["dragenter", "dragover"].forEach((ev) =>
        document.addEventListener(ev, (e) => {
          e.preventDefault(); opts.drop.classList.add("on");
        }));
      ["dragleave", "drop"].forEach((ev) =>
        document.addEventListener(ev, (e) => {
          e.preventDefault();
          if (ev === "dragleave" && e.relatedTarget) return;
          opts.drop.classList.remove("on");
        }));
      document.addEventListener("drop", (e) => {
        if (e.dataTransfer && e.dataTransfer.files.length)
          addLocal(e.dataTransfer.files, opts.select);
      });
    }

    return loadList(opts.select);
  }

  try {
    const saved = localStorage.getItem("fm-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) { /* private mode */ }

  return { state, wire, activate, addLocal, download, parseFont, status, el };
})();
