(function(){
  const normalize = (value) => String(value || "").normalize("NFKC").toLowerCase().replace(/[\s_\-/.]+/g, " ").trim();
  const compact = (value) => normalize(value).replace(/ /g, "");
  const navStateKey = "aimt-guide-nav-open";
  const themeKey = "aimt-guide-theme";
  const sidebarWidthKey = "aimt-guide-sidebar-width";
  const sidebarCollapsedKey = "aimt-guide-sidebar-collapsed";
  const minSidebarWidth = 240;
  const maxSidebarWidth = 520;
  const themeLabels = {
    system: {text: "◐", title: "테마: 기기 설정"},
    dark: {text: "☾", title: "테마: 다크"},
    light: {text: "☀", title: "테마: 라이트"}
  };
  function readTheme(){
    try {
      const theme = localStorage.getItem(themeKey);
      return theme === "light" || theme === "dark" ? theme : "system";
    } catch (_) {
      return "system";
    }
  }
  function writeTheme(theme){
    try {
      if (theme === "system") localStorage.removeItem(themeKey);
      else localStorage.setItem(themeKey, theme);
    } catch (_) {}
  }
  function applyTheme(theme){
    if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
    else document.documentElement.removeAttribute("data-theme");
    const button = document.getElementById("themeToggle");
    if (!button) return;
    const label = themeLabels[theme] || themeLabels.system;
    button.textContent = label.text;
    button.title = label.title;
    button.setAttribute("aria-label", label.title);
  }
  function setupThemeToggle(){
    const button = document.getElementById("themeToggle");
    let theme = readTheme();
    applyTheme(theme);
    if (!button) return;
    button.addEventListener("click", () => {
      theme = theme === "system" ? "dark" : theme === "dark" ? "light" : "system";
      writeTheme(theme);
      applyTheme(theme);
    });
    const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
    if (media) media.addEventListener("change", () => { if (readTheme() === "system") applyTheme("system"); });
  }
  function clampSidebarWidth(value){
    const maxByViewport = Math.max(minSidebarWidth, Math.min(maxSidebarWidth, Math.floor(window.innerWidth * 0.48)));
    return Math.min(maxByViewport, Math.max(minSidebarWidth, Math.round(value)));
  }
  function applySidebarWidth(width){
    const nextWidth = clampSidebarWidth(width);
    document.documentElement.style.setProperty("--sidebar-width", nextWidth + "px");
    const resizer = document.getElementById("sidebarResizer");
    if (resizer) resizer.setAttribute("aria-valuenow", String(nextWidth));
    return nextWidth;
  }
  function readSidebarWidth(){
    try {
      const width = Number(localStorage.getItem(sidebarWidthKey));
      return Number.isFinite(width) && width > 0 ? width : 310;
    } catch (_) {
      return 310;
    }
  }
  function writeSidebarWidth(width){
    try { localStorage.setItem(sidebarWidthKey, String(width)); } catch (_) {}
  }
  function readSidebarCollapsed(){
    try { return localStorage.getItem(sidebarCollapsedKey) === "1"; } catch (_) { return false; }
  }
  function writeSidebarCollapsed(collapsed){
    try {
      if (collapsed) localStorage.setItem(sidebarCollapsedKey, "1");
      else localStorage.removeItem(sidebarCollapsedKey);
    } catch (_) {}
  }
  function applySidebarCollapsed(collapsed){
    if (collapsed) document.documentElement.dataset.sidebar = "collapsed";
    else document.documentElement.removeAttribute("data-sidebar");
    const expandButton = document.getElementById("sidebarExpand");
    const collapseButton = document.getElementById("sidebarCollapse");
    if (expandButton) expandButton.setAttribute("aria-expanded", String(!collapsed));
    if (collapseButton) collapseButton.setAttribute("aria-expanded", String(!collapsed));
  }
  function setupSidebarCollapse(){
    const expandButton = document.getElementById("sidebarExpand");
    const collapseButton = document.getElementById("sidebarCollapse");
    let collapsed = readSidebarCollapsed();
    applySidebarCollapsed(collapsed);
    function setCollapsed(nextCollapsed){
      collapsed = nextCollapsed;
      writeSidebarCollapsed(collapsed);
      applySidebarCollapsed(collapsed);
    }
    if (collapseButton) collapseButton.addEventListener("click", () => setCollapsed(true));
    if (expandButton) expandButton.addEventListener("click", () => setCollapsed(false));
  }
  function setupSidebarResize(){
    const resizer = document.getElementById("sidebarResizer");
    if (!resizer) return;
    let currentWidth = applySidebarWidth(readSidebarWidth());
    resizer.setAttribute("aria-valuemin", String(minSidebarWidth));
    resizer.setAttribute("aria-valuemax", String(maxSidebarWidth));
    resizer.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      resizer.setPointerCapture(event.pointerId);
      document.body.classList.add("is-resizing-sidebar");
    });
    resizer.addEventListener("pointermove", (event) => {
      if (!resizer.hasPointerCapture(event.pointerId)) return;
      currentWidth = applySidebarWidth(event.clientX);
    });
    function endResize(event){
      if (!resizer.hasPointerCapture(event.pointerId)) return;
      resizer.releasePointerCapture(event.pointerId);
      document.body.classList.remove("is-resizing-sidebar");
      writeSidebarWidth(currentWidth);
    }
    resizer.addEventListener("pointerup", endResize);
    resizer.addEventListener("pointercancel", endResize);
    resizer.addEventListener("keydown", (event) => {
      const delta = event.key === "ArrowLeft" ? -16 : event.key === "ArrowRight" ? 16 : 0;
      if (!delta) return;
      event.preventDefault();
      currentWidth = applySidebarWidth(currentWidth + delta);
      writeSidebarWidth(currentWidth);
    });
    window.addEventListener("resize", () => {
      currentWidth = applySidebarWidth(currentWidth);
      writeSidebarWidth(currentWidth);
    });
  }
  function readNavState(){
    try { return JSON.parse(localStorage.getItem(navStateKey) || "{}"); } catch (_) { return {}; }
  }
  function writeNavState(state){
    try { localStorage.setItem(navStateKey, JSON.stringify(state)); } catch (_) {}
  }
  function setupNavGroups(){
    const state = readNavState();
    document.querySelectorAll(".nav-group").forEach((group) => {
      const link = group.querySelector(":scope > summary .nav-link[href]");
      if (!link) return;
      const key = new URL(link.getAttribute("href"), location.href).pathname.replace(/\/index\.html$/, "/");
      if (Object.prototype.hasOwnProperty.call(state, key)) group.open = Boolean(state[key]);
      link.addEventListener("click", (event) => event.stopPropagation());
      group.addEventListener("toggle", () => {
        const next = readNavState();
        next[key] = group.open;
        writeNavState(next);
      });
    });
  }
  function markCurrent(){
    const current = new URL(location.href).pathname.replace(/\/index\.html$/, "/");
    document.querySelectorAll(".nav-link[href]").forEach((link) => {
      const target = new URL(link.getAttribute("href"), location.href).pathname.replace(/\/index\.html$/, "/");
      if (target === current) {
        link.setAttribute("aria-current", "page");
        let parent = link.closest("details");
        while (parent) { parent.open = true; parent = parent.parentElement.closest("details"); }
      }
    });
  }
  async function setupSearch(){
    const input = document.getElementById("guideSearch");
    const results = document.getElementById("searchResults");
    const script = document.currentScript;
    if (!input || !results || !script) return;
    let index = [];
    try { index = await fetch(new URL("../search-index.json", script.src)).then((res) => res.json()); } catch (_) { return; }
    input.addEventListener("input", () => {
      const query = normalize(input.value);
      const compactQuery = compact(input.value);
      results.innerHTML = "";
      if (!query) { results.hidden = true; return; }
      const tokens = query.split(" ").filter(Boolean);
      const matches = index.map((item) => {
        const haystack = normalize([item.title, item.path, item.body].join(" "));
        const tight = compact([item.title, item.path, item.body].join(" "));
        let score = 0;
        if (haystack.includes(query)) score += 8;
        if (tight.includes(compactQuery)) score += 6;
        score += tokens.filter((token) => haystack.includes(token) || tight.includes(token.replace(/ /g, ""))).length;
        return {item, score};
      }).filter((row) => row.score > 0).sort((a,b) => b.score - a.score).slice(0, 12);
      results.hidden = matches.length === 0;
      for (const row of matches) {
        const a = document.createElement("a");
        a.href = new URL(row.item.url, new URL("..", script.src)).toString();
        a.textContent = row.item.title;
        results.appendChild(a);
      }
    });
  }
  setupThemeToggle();
  setupSidebarCollapse();
  setupSidebarResize();
  setupNavGroups();
  markCurrent();
  setupSearch();
})();