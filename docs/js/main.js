/* FlashBot documentation site: theme, copy buttons, docs navigation. */
(function () {
  "use strict";

  var root = document.documentElement;
  var STORAGE_KEY = "flashbot-theme";

  function storedTheme() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function saveTheme(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) { /* storage unavailable */ }
  }

  function effectiveTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit) return explicit;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  /* Theme ---------------------------------------------------------------- */

  var saved = storedTheme();
  if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);

  document.querySelectorAll(".theme-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = effectiveTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      saveTheme(next);
    });
  });

  /* Copy buttons ---------------------------------------------------------- */

  function copyText(text, button) {
    var done = function () {
      var label = button.textContent;
      button.textContent = "Copied";
      setTimeout(function () { button.textContent = label; }, 1400);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () {});
      return;
    }
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "absolute";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ }
    document.body.removeChild(area);
  }

  document.querySelectorAll(".command").forEach(function (el) {
    var button = el.querySelector(".copy-btn");
    var code = el.querySelector("code");
    if (button && code) {
      button.addEventListener("click", function () { copyText(code.textContent.trim(), button); });
    }
  });

  document.querySelectorAll(".doc pre").forEach(function (pre) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-btn";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code");
    button.addEventListener("click", function () {
      var code = pre.querySelector("code") || pre;
      copyText(code.textContent.replace(/\s+$/, ""), button);
    });
    pre.appendChild(button);
  });

  /* Heading anchors ------------------------------------------------------- */

  document.querySelectorAll(".doc h2[id], .doc h3[id]").forEach(function (h) {
    var a = document.createElement("a");
    a.className = "anchor";
    a.href = "#" + h.id;
    a.textContent = "#";
    a.setAttribute("aria-label", "Link to this section");
    h.appendChild(a);
  });

  /* Sidebar: mobile toggle, filter, active section ------------------------- */

  var sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  var body = document.body;
  var toggle = document.querySelector(".menu-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = body.classList.toggle("sidebar-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
  sidebar.addEventListener("click", function (e) {
    if (e.target.closest("a")) {
      body.classList.remove("sidebar-open");
      if (toggle) toggle.setAttribute("aria-expanded", "false");
    }
  });

  var search = sidebar.querySelector(".sidebar-search");
  var noResults = sidebar.querySelector(".no-results");
  if (search) {
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var visible = 0;
      sidebar.querySelectorAll("ul").forEach(function (list) {
        var shown = 0;
        list.querySelectorAll("li").forEach(function (li) {
          var target = document.getElementById(li.querySelector("a").getAttribute("href").slice(1));
          var haystack = li.textContent + " " + (target ? target.textContent : "");
          var match = !q || haystack.toLowerCase().indexOf(q) !== -1;
          li.style.display = match ? "" : "none";
          if (match) shown++;
        });
        list.style.display = shown ? "" : "none";
        var heading = list.previousElementSibling;
        if (heading && heading.tagName === "H4") heading.style.display = shown ? "" : "none";
        visible += shown;
      });
      if (noResults) noResults.style.display = visible ? "none" : "block";
    });
  }

  var links = Array.prototype.slice.call(sidebar.querySelectorAll("a[href^='#']"));
  var sections = links
    .map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); })
    .filter(Boolean);

  function setActive(id) {
    links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + id); });
  }

  if ("IntersectionObserver" in window && sections.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: "-80px 0px -70% 0px" });
    sections.forEach(function (s) { observer.observe(s); });
  }
})();
