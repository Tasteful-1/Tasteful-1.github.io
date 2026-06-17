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
    const openButton = document.getElementById("searchOpen");
    const overlay = document.getElementById("searchOverlay");
    const dialog = overlay ? overlay.querySelector(".search-dialog") : null;
    const closeButton = document.getElementById("searchClose");
    const input = document.getElementById("guideSearch");
    const results = document.getElementById("searchResults");
    const script = document.currentScript;
    if (!openButton || !overlay || !dialog || !closeButton || !input || !results || !script) return;
    let index = [];
    try { index = await fetch(new URL("../search-index.json", script.src)).then((res) => res.json()); } catch (_) { return; }
    function closeSearch(){
      overlay.hidden = true;
      document.body.classList.remove("is-search-open");
      openButton.focus();
    }
    function openSearch(){
      overlay.hidden = false;
      document.body.classList.add("is-search-open");
      input.focus();
      input.select();
      renderSearchResults();
    }
    function makeBadge(text){
      const badge = document.createElement("span");
      badge.className = "search-badge";
      badge.textContent = text;
      return badge;
    }
    function makeSnippet(item, query){
      const body = String(item.body || "").replace(/\s+/g, " ").trim();
      if (!body) return "";
      const source = normalize(body);
      const offset = source.indexOf(query);
      if (offset < 0) return body.slice(0, 120);
      return body.slice(Math.max(0, offset - 36), offset + 96);
    }
    function scoreItem(item, query, compactQuery, tokens){
      const title = normalize(item.title);
      const tightTitle = compact(item.title);
      const body = normalize(item.body);
      const tightBody = compact(item.body);
      const titleMatched = Boolean(query) && (title.includes(query) || tightTitle.includes(compactQuery) || tokens.some((token) => title.includes(token) || tightTitle.includes(token)));
      const bodyMatched = Boolean(query) && (body.includes(query) || tightBody.includes(compactQuery) || tokens.some((token) => body.includes(token) || tightBody.includes(token)));
      let score = 0;
      if (title.includes(query)) score += 16;
      if (tightTitle.includes(compactQuery)) score += 12;
      if (body.includes(query)) score += 8;
      if (tightBody.includes(compactQuery)) score += 6;
      score += tokens.filter((token) => title.includes(token) || tightTitle.includes(token)).length * 4;
      score += tokens.filter((token) => body.includes(token) || tightBody.includes(token)).length;
      return {item, score, titleMatched, bodyMatched};
    }
    function renderSearchResults(){
      const query = normalize(input.value);
      const compactQuery = compact(input.value);
      results.innerHTML = "";
      if (!query) {
        results.hidden = false;
        const empty = document.createElement("div");
        empty.className = "search-empty";
        empty.textContent = "검색어를 입력하세요.";
        results.appendChild(empty);
        return;
      }
      const tokens = query.split(" ").filter(Boolean);
      const matches = index.map((item) => scoreItem(item, query, compactQuery, tokens))
        .filter((row) => row.score > 0 && (row.titleMatched || row.bodyMatched))
        .sort((a,b) => b.score - a.score)
        .slice(0, 20);
      results.hidden = false;
      if (!matches.length) {
        const empty = document.createElement("div");
        empty.className = "search-empty";
        empty.textContent = "검색 결과가 없습니다.";
        results.appendChild(empty);
        return;
      }
      for (const row of matches) {
        const a = document.createElement("a");
        a.href = new URL(row.item.url, new URL("..", script.src)).toString();
        const title = document.createElement("span");
        title.className = "search-result-title";
        title.textContent = row.item.title;
        const badges = document.createElement("span");
        badges.className = "search-badges";
        if (row.titleMatched) badges.appendChild(makeBadge("제목"));
        if (row.bodyMatched) badges.appendChild(makeBadge("내용"));
        const snippetText = row.bodyMatched && !row.titleMatched ? makeSnippet(row.item, query) : "";
        a.append(title, badges);
        if (snippetText) {
          const snippet = document.createElement("span");
          snippet.className = "search-snippet";
          snippet.textContent = snippetText;
          a.appendChild(snippet);
        }
        results.appendChild(a);
      }
    }
    openButton.addEventListener("click", openSearch);
    closeButton.addEventListener("click", closeSearch);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) closeSearch(); });
    dialog.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const tag = document.activeElement ? document.activeElement.tagName : "";
        if (tag !== "INPUT" && tag !== "TEXTAREA") { event.preventDefault(); openSearch(); }
      }
      if (event.key === "Escape" && !overlay.hidden) closeSearch();
    });
    input.addEventListener("input", renderSearchResults);
  }  setupThemeToggle();
  setupSidebarCollapse();
  setupSidebarResize();
  setupNavGroups();
  markCurrent();
  setupSearch();
})();