/* Showcase page. The demos are static markup in showcase.html; all this does
 * is switch between them and scale the base size. Font loading lives in
 * fontkit.js.
 *
 * Which demo is showing is held in the URL hash rather than in a variable, so
 * each one is linkable from the nav on either page and the back button works.
 */

const $ = (s) => document.querySelector(s);
const stage = $("#stage");
const DEMOS = ["blog", "brutal", "dash"];

function fromHash() {
  const h = location.hash.replace(/^#/, "");
  return DEMOS.includes(h) ? h : DEMOS[0];
}

function setDemo(name) {
  stage.dataset.demo = name;
  document.querySelectorAll("#bar .pages a").forEach((a) => {
    if (a.dataset.demo === name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
}

window.addEventListener("hashchange", () => setDemo(fromHash()));
setDemo(fromHash());

$("#base").addEventListener("input", () => {
  const v = $("#base").value;
  $("#baseout").value = v;
  stage.style.setProperty("--base", v + "px");
});

$("#baseout").value = $("#base").value;
stage.style.setProperty("--base", $("#base").value + "px");

FontKit.wire({
  select: $("#font"),
  upload: $("#upload"),
  download: $("#download"),
  drop: $("#drop"),
  status: $("#status"),
});
