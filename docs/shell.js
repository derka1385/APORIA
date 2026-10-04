/* APORIA site shell: the one header every page shares.
 * The research-directions finder (React, docs/index.html) renders the same header in
 * directions/web/src/components/Layout.tsx; the static pages (divergence/, lab/) load this script:
 *   <script src="../shell.js" data-active="divergence" data-sections="results:Results,method:Method"></script>
 * Keep the two in step: same mark, label, nav order and styles. */
(function () {
  var me = document.currentScript;
  var base = new URL(".", me.src).href; // .../APORIA/docs/
  var active = me.getAttribute("data-active") || "";
  var sections = (me.getAttribute("data-sections") || "").split(",").filter(Boolean);
  var NAV = [
    ["topics", "Topics", "topics"],
    ["directions", "Directions", "briefs"],
    ["runs", "Runs", "runs"],
    ["atlas", "Atlas", "atlas"],
    ["results", "Results", "results"],
    ["about", "About", "about"],
    ["reasoners", "Reasoners", "lab/"],
    ["divergence", "Divergence", "divergence/"],
  ];
  var font = document.createElement("link");
  font.rel = "stylesheet";
  font.href = "https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap";
  document.head.appendChild(font);
  var css = document.createElement("style");
  css.textContent = [
    ".apo-top{position:sticky;top:0;z-index:30;background:rgba(18,20,22,.92);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);border-bottom:1px solid #353B42}",
    ".apo-top .in{max-width:1400px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:center;gap:8px 24px;min-height:56px;padding:8px 24px;box-sizing:border-box}",
    ".apo-top a{text-decoration:none}",
    ".apo-mark{display:flex;align-items:center;gap:10px;font:600 15px/1.2 'Source Sans 3',system-ui,sans-serif;letter-spacing:.11em;color:#F4F1E9}",
    ".apo-mark svg{width:22px;height:22px}",
    ".apo-sub{font:12px/1.4 'IBM Plex Mono',ui-monospace,monospace;color:#B4BBC2}",
    ".apo-sub:hover{color:#F4F1E9}",
    ".apo-nav{margin-left:auto}",
    ".apo-nav ul{display:flex;flex-wrap:wrap;gap:4px 20px;list-style:none;margin:0;padding:0;font:13px/1.5 'IBM Plex Mono',ui-monospace,monospace}",
    ".apo-nav a{color:#B4BBC2}",
    ".apo-nav a:hover{color:#F4F1E9}",
    ".apo-nav a[aria-current=page]{color:#F4F1E9;text-decoration:underline;text-underline-offset:6px}",
    ".apo-onpage{max-width:1400px;margin:0 auto;padding:10px 24px 0;box-sizing:border-box;font:12px/1.6 'IBM Plex Mono',ui-monospace,monospace;color:#808A94}",
    ".apo-onpage a{color:#B4BBC2;margin-left:14px;text-decoration:none}",
    ".apo-onpage a:hover{color:#F4F1E9}",
    "@media (max-width:640px){.apo-top .in{padding:8px 16px}.apo-onpage{padding:10px 16px 0}}",
  ].join("");
  document.head.appendChild(css);
  var mark =
    '<svg viewBox="0 0 128 128" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="8">' +
    '<path d="M108.184 45.245 A48 48 0 1 1 64.838 16.007"/><path d="M93.875 75.468 A32 32 0 1 1 86.627 41.373"/>' +
    '<path d="M70.762 78.501 A16 16 0 1 1 79.998 63.721"/></g></svg>';
  var items = NAV.map(function (n) {
    return '<li><a href="' + base + n[2] + '"' + (n[0] === active ? ' aria-current="page"' : "") + ">" + n[1] + "</a></li>";
  }).join("");
  var header = document.createElement("header");
  header.className = "apo-top";
  header.innerHTML =
    '<div class="in"><a class="apo-mark" href="' + base + '">' + mark + "APORIA</a>" +
    '<a class="apo-sub" href="' + base + '">research directions</a>' +
    '<nav class="apo-nav" aria-label="Main"><ul>' + items + "</ul></nav></div>";
  document.body.insertBefore(header, document.body.firstChild);
  if (sections.length) {
    var row = document.createElement("div");
    row.className = "apo-onpage";
    row.innerHTML = "On this page:" + sections.map(function (s) {
      var p = s.split(":");
      return '<a href="#' + p[0] + '">' + p[1] + "</a>";
    }).join("");
    header.insertAdjacentElement("afterend", row);
  }
})();
