/* Showcase page. The demos are static markup in showcase.html; all this does
 * is switch between them, scale the base size, and keep the choice across
 * reloads. Font loading lives in fontkit.js. */

const $ = (s) => document.querySelector(s);
const stage = $("#stage");

function setDemo(name) {
  stage.dataset.demo = name;
  document.querySelectorAll("#bar .tabs button").forEach((b) =>
    b.classList.toggle("on", b.dataset.demo === name));
  try { localStorage.setItem("fm-demo", name); } catch (e) { /* private mode */ }
}

document.querySelectorAll("#bar .tabs button").forEach((b) =>
  b.addEventListener("click", () => setDemo(b.dataset.demo)));

$("#base").addEventListener("input", () => {
  const v = $("#base").value;
  $("#baseout").value = v;
  stage.style.setProperty("--base", v + "px");
});

try {
  const saved = localStorage.getItem("fm-demo");
  if (saved) setDemo(saved);
} catch (e) { /* private mode */ }

$("#baseout").value = $("#base").value;
stage.style.setProperty("--base", $("#base").value + "px");

FontKit.wire({
  select: $("#font"),
  upload: $("#upload"),
  download: $("#download"),
  drop: $("#drop"),
  status: $("#status"),
});
