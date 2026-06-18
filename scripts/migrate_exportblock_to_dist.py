from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urldefrag, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

SITE_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = SITE_ROOT / "ExportBlock"
DIST_ROOT = SITE_ROOT / "dist"
GUIDE_ROOT = DIST_ROOT / "guide"
STATIC_ROOT = GUIDE_ROOT / "static"
ASSET_ROOT = GUIDE_ROOT / "assets"
UUID_RE = re.compile(r"([0-9a-f]{32})", re.IGNORECASE)
LOCAL_SCHEMES = {"", None}


@dataclass
class Page:
    source_path: Path
    title: str
    slug: str
    version: str
    edited_at: str
    depth: int = 0
    children: list[Path] = field(default_factory=list)

    @property
    def output_path(self) -> Path:
        return GUIDE_ROOT / "index.html" if not self.slug else GUIDE_ROOT / self.slug / "index.html"

    @property
    def relative_output(self) -> str:
        return self.output_path.relative_to(DIST_ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def is_external_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme not in LOCAL_SCHEMES or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:"))


def strip_notion_id(value: str) -> str:
    return re.sub(r"\s+[0-9a-f]{32}$", "", value, flags=re.IGNORECASE).strip()


def extract_short_id(path: Path) -> str:
    match = UUID_RE.search(path.stem)
    return match.group(1)[-8:].lower() if match else path.stem[-8:].lower()


def parse_title(path: Path) -> str:
    soup = BeautifulSoup(read_text(path), "html.parser")
    page_title = soup.select_one(".page-title")
    if page_title:
        title = page_title.get_text(" ", strip=True)
        if title:
            return title
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return strip_notion_id(path.stem)


def parse_version(soup: BeautifulSoup) -> str:
    version_cell = soup.select_one(".property-row-multi_select td")
    if version_cell:
        version = version_cell.get_text(" ", strip=True)
        if version:
            return version
    body_text = soup.get_text(" ", strip=True)
    match = re.search(r"AIMT\s+PRO\s+([0-9]+(?:\.[0-9]+)+)", body_text, flags=re.IGNORECASE)
    return f"AIMT PRO {match.group(1)}" if match else "미기재"


def parse_edited_at(path: Path, soup: BeautifulSoup) -> str:
    edited_time = soup.select_one(".property-row-last_edited_time time")
    if edited_time:
        value = edited_time.get_text(" ", strip=True)
        if value:
            return value
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def parse_page_metadata(path: Path) -> tuple[str, str, str]:
    soup = BeautifulSoup(read_text(path), "html.parser")
    page_title = soup.select_one(".page-title")
    if page_title:
        title = page_title.get_text(" ", strip=True)
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    else:
        title = strip_notion_id(path.stem)
    return title, parse_version(soup), parse_edited_at(path, soup)


def normalize_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    slug = re.sub(r"[^\w가-힣-]+", "-", normalized, flags=re.UNICODE).strip("-_")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "page"


def make_unique_slug(title: str, source_path: Path, used_slugs: set[str]) -> str:
    base = normalize_slug(title)
    slug = base
    if slug in used_slugs:
        slug = f"{base}-{extract_short_id(source_path)}"
    suffix = 2
    while slug in used_slugs:
        slug = f"{base}-{extract_short_id(source_path)}-{suffix}"
        suffix += 1
    used_slugs.add(slug)
    return slug


def resolve_local_path(base_path: Path, raw_url: str) -> Path | None:
    url, _fragment = urldefrag(raw_url.strip())
    if not url or is_external_url(url):
        return None
    path = (base_path.parent / unquote(url)).resolve()
    try:
        path.relative_to(EXPORT_ROOT.resolve())
    except ValueError:
        return None
    return path


def resolve_html_target(base_path: Path, raw_url: str, known_paths: set[Path]) -> Path | None:
    path = resolve_local_path(base_path, raw_url)
    if path is None:
        return None
    if path.suffix.lower() != ".html":
        return None
    resolved = path.resolve()
    return resolved if resolved in known_paths else None


def find_root_page(html_paths: list[Path]) -> Path:
    top_level = [path for path in html_paths if path.parent == EXPORT_ROOT]
    if not top_level:
        raise FileNotFoundError("ExportBlock 루트 HTML을 찾지 못했습니다.")
    preferred = [path for path in top_level if "aimt" in path.name.lower()]
    return sorted(preferred or top_level, key=lambda path: path.name)[0]


def collect_child_pages(path: Path, known_paths: set[Path]) -> list[Path]:
    child_dir = path.parent / strip_notion_id(path.stem)
    direct_children = {child.resolve() for child in child_dir.glob("*.html")} if child_dir.exists() else set()
    direct_children &= known_paths
    if not direct_children:
        return []

    soup = BeautifulSoup(read_text(path), "html.parser")
    linked: list[Path] = []
    seen: set[Path] = set()
    for anchor in soup.find_all("a", href=True):
        target = resolve_html_target(path, str(anchor["href"]), known_paths)
        if target is None or target not in direct_children or target in seen:
            continue
        linked.append(target)
        seen.add(target)
    for child in sorted(direct_children, key=lambda item: item.name):
        if child not in seen:
            linked.append(child)
    return linked


def build_pages() -> tuple[list[Page], dict[Path, Page]]:
    if not EXPORT_ROOT.exists():
        raise FileNotFoundError(f"ExportBlock 폴더가 없습니다: {EXPORT_ROOT}")
    html_paths = sorted(path.resolve() for path in EXPORT_ROOT.rglob("*.html"))
    if not html_paths:
        raise FileNotFoundError("ExportBlock 안에 HTML 파일이 없습니다.")

    root_path = find_root_page(html_paths).resolve()
    used_slugs: set[str] = set()
    page_map: dict[Path, Page] = {}
    for path in html_paths:
        title, version, edited_at = parse_page_metadata(path)
        slug = "" if path == root_path else make_unique_slug(title, path, used_slugs)
        page_map[path] = Page(source_path=path, title=title, slug=slug, version=version, edited_at=edited_at)

    known_paths = set(page_map)
    for page in page_map.values():
        page.children = collect_child_pages(page.source_path, known_paths)

    ordered: list[Page] = []
    visited: set[Path] = set()

    def visit(path: Path, depth: int) -> None:
        if path in visited:
            return
        visited.add(path)
        page = page_map[path]
        page.depth = depth
        ordered.append(page)
        for child_path in page.children:
            visit(child_path, depth + 1)

    visit(root_path, 0)

    for path in html_paths:
        if path in visited:
            continue
        page = page_map[path]
        page.depth = max(1, len(path.relative_to(EXPORT_ROOT).parent.parts))
        ordered.append(page)
        visited.add(path)

    return ordered, page_map


def relative_href(from_path: Path, to_path: Path) -> str:
    relative = to_path.resolve().relative_to(DIST_ROOT.resolve())
    base = from_path.parent.resolve().relative_to(DIST_ROOT.resolve())
    prefix = [".."] * len(base.parts)
    value = Path(*prefix, *relative.parts).as_posix() if prefix else relative.as_posix()
    return quote(value, safe="/._-#%")


def copy_asset(page: Page, base_path: Path, raw_url: str) -> str:
    url, fragment = urldefrag(raw_url.strip())
    source_path = resolve_local_path(base_path, url)
    if source_path is None or not source_path.exists() or source_path.suffix.lower() == ".html":
        return raw_url
    target_dir = ASSET_ROOT / (page.slug or "home")
    target_path = target_dir / source_path.name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    suffix = f"#{fragment}" if fragment else ""
    return f"{relative_href(page.output_path, target_path)}{suffix}"


def rewrite_fragment_links(fragment: BeautifulSoup, page: Page, page_map: dict[Path, Page]) -> None:
    known_paths = set(page_map)
    for tag in fragment.find_all(True):
        if not isinstance(tag, Tag):
            continue
        if tag.name == "a" and tag.has_attr("href"):
            raw_href = str(tag["href"])
            target = resolve_html_target(page.source_path, raw_href, known_paths)
            if target is not None:
                tag["href"] = relative_href(page.output_path, page_map[target].output_path)
                continue
            tag["href"] = copy_asset(page, page.source_path, raw_href)
        if tag.name == "img" and tag.has_attr("src"):
            tag["src"] = copy_asset(page, page.source_path, str(tag["src"]))


def extract_body_fragment(page: Page, page_map: dict[Path, Page]) -> str:
    soup = BeautifulSoup(read_text(page.source_path), "html.parser")
    body = soup.select_one(".page-body")
    if body is None:
        body = soup.select_one("article.page") or soup.body
    body_html = "".join(str(child) for child in body.contents) if body else ""
    fragment = BeautifulSoup(body_html, "html.parser")
    rewrite_fragment_links(fragment, page, page_map)
    return "".join(str(child) for child in fragment.contents).strip()


def make_nav(pages: list[Page], from_path: Path) -> str:
    lines: list[str] = []
    stack: list[int] = []
    for index, page in enumerate(pages):
        next_depth = pages[index + 1].depth if index + 1 < len(pages) else -1
        while stack and stack[-1] >= page.depth:
            lines.append("</div></details>")
            stack.pop()
        title = html.escape(page.title, quote=False)
        href = relative_href(from_path, page.output_path)
        anchor = f'<a class="nav-link" href="{href}" data-depth="{page.depth}">{title}</a>'
        if next_depth > page.depth:
            open_attr = " open" if page.depth == 0 else ""
            nav_key = html.escape(page.output_path.relative_to(DIST_ROOT).as_posix(), quote=True)
            lines.append(f'<details class="nav-group" data-depth="{page.depth}" data-nav-key="{nav_key}"{open_attr}><summary><span class="nav-caret" aria-hidden="true"></span>{anchor}</summary><div class="nav-children">')
            stack.append(page.depth)
        else:
            lines.append(anchor)
    while stack:
        lines.append("</div></details>")
        stack.pop()
    return "\n".join(lines)


def render_page(page: Page, pages: list[Page], body: str) -> str:
    title = html.escape(page.title, quote=False)
    version = html.escape(page.version, quote=False)
    edited_at = html.escape(page.edited_at, quote=False)
    css_href = relative_href(page.output_path, STATIC_ROOT / "styles.css")
    js_href = relative_href(page.output_path, STATIC_ROOT / "main.js")
    home_href = relative_href(page.output_path, GUIDE_ROOT / "index.html")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · AIMT Guide</title>
  <script>(function(){{document.documentElement.dataset.navRestoring="1";try{{var theme=localStorage.getItem("aimt-guide-theme");if(theme==="light"||theme==="dark")document.documentElement.dataset.theme=theme;if(localStorage.getItem("aimt-guide-sidebar-collapsed")==="1")document.documentElement.dataset.sidebar="collapsed";}}catch(_){{}}}})();</script>
  <style id="navRestoreStyle">:root[data-nav-restoring="1"] .nav-list{{visibility:hidden}}:root[data-nav-restoring="1"] .nav-caret{{transition:none}}</style>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
  <button id="sidebarExpand" class="sidebar-expand sidebar-toggle" type="button" aria-label="사이드바 열기" title="사이드바 열기">☰</button>
  <div id="searchOverlay" class="search-overlay" hidden>
    <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="searchTitle">
      <div class="search-header"><h2 id="searchTitle">문서 검색</h2><button id="searchClose" class="search-close" type="button" aria-label="검색 닫기" title="검색 닫기">×</button></div>
      <input id="guideSearch" class="search-input" type="search" placeholder="검색어 입력" autocomplete="off">
      <div id="searchResults" class="search-results" hidden></div>
    </section>
  </div>
  <div class="site-shell">
    <aside class="sidebar">
      <div class="brand-row"><a class="brand" href="{home_href}">AIMT GUIDE</a><button id="searchOpen" class="sidebar-toggle" type="button" aria-label="문서 검색" title="문서 검색">⌕</button><button id="themeToggle" class="theme-toggle" type="button" aria-label="테마 변경" title="테마 변경">◐</button><button id="sidebarCollapse" class="sidebar-toggle" type="button" aria-label="사이드바 닫기" title="사이드바 닫기">←</button></div>
      
      <nav class="nav-list" aria-label="문서 목록">
{make_nav(pages, page.output_path)}
      </nav>
    </aside>
    <div id="sidebarResizer" class="sidebar-resizer" role="separator" aria-label="사이드바 너비 조절" aria-orientation="vertical" tabindex="0"></div>
    <main class="content-shell">
      <article class="guide-content">
        <h1>{title}</h1>
        <p class="doc-version">작성 당시 버전: {version}<br>최종 편집 일시: {edited_at}</p>
{body}
      </article>
    </main>
  </div>
  <script src="{js_href}"></script>
</body>
</html>
"""


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(value, "html.parser").get_text(" ", strip=True)).strip()


def write_search_index(pages: list[Page], page_bodies: dict[Path, str]) -> None:
    entries = [
        {
            "title": page.title,
            "url": relative_href(GUIDE_ROOT / "index.html", page.output_path),
            "path": page.relative_output,
            "body": plain_text(page_bodies[page.source_path]),
        }
        for page in pages
    ]
    write_text(GUIDE_ROOT / "search-index.json", json.dumps(entries, ensure_ascii=False, indent=2))


def write_static_assets() -> None:
    write_text(
        STATIC_ROOT / "styles.css",
        """
""".strip(),
    )
    write_text(
        STATIC_ROOT / "main.js",
        """
(function(){
  const normalize = (value) => String(value || "").normalize("NFKC").toLowerCase().replace(/[\\s_\\-/.]+/g, " ").trim();
  const compact = (value) => normalize(value).replace(/ /g, "");
  const navStateKey = "aimt-guide-nav-open";
  const sidebarScrollKey = "aimt-guide-sidebar-scroll";
  const themeKey = "aimt-guide-theme";
  const sidebarWidthKey = "aimt-guide-sidebar-width";
  const sidebarCollapsedKey = "aimt-guide-sidebar-collapsed";
  const minSidebarWidth = 240;
  const maxSidebarWidth = 520;
  let isRestoringNav = true;
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
  function navGroupKey(group){
    const link = group.querySelector(":scope > summary .nav-link[href]");
    const storedKey = group.getAttribute("data-nav-key");
    const legacyKey = link ? new URL(link.getAttribute("href"), location.href).pathname.replace(/\\/index\\.html$/, "/") : "";
    return {
      key: storedKey ? "group:" + storedKey : legacyKey,
      legacyKey
    };
  }
  function snapshotNavState(){
    const next = readNavState();
    document.querySelectorAll(".nav-group").forEach((group) => {
      const keys = navGroupKey(group);
      if (!keys.key) return;
      next[keys.key] = group.open;
    });
    writeNavState(next);
  }
  function readSidebarScroll(){
    try {
      const value = Number(sessionStorage.getItem(sidebarScrollKey));
      return Number.isFinite(value) && value >= 0 ? value : null;
    } catch (_) {
      return null;
    }
  }
  function writeSidebarScroll(value){
    try { sessionStorage.setItem(sidebarScrollKey, String(Math.max(0, Math.round(value)))); } catch (_) {}
  }
  function normalizeDocumentPath(pathname){
    return pathname.replace(/\\/index\\.html?$/, "/");
  }
  function absolutizeShellLinks(){
    document.querySelectorAll(".sidebar a[href], .brand[href]").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      try { link.setAttribute("href", new URL(href, location.href).href); } catch (_) {}
    });
  }
  function setupNavGroups(){
    const state = readNavState();
    document.querySelectorAll(".nav-group").forEach((group) => {
      const link = group.querySelector(":scope > summary .nav-link[href]");
      const keys = navGroupKey(group);
      const key = keys.key;
      const legacyKey = keys.legacyKey;
      if (!key) return;
      if (Object.prototype.hasOwnProperty.call(state, key)) group.open = Boolean(state[key]);
      else if (legacyKey && Object.prototype.hasOwnProperty.call(state, legacyKey)) group.open = Boolean(state[legacyKey]);
      if (link) link.addEventListener("click", (event) => event.stopPropagation());
      group.addEventListener("toggle", () => {
        if (isRestoringNav) return;
        const next = readNavState();
        next[key] = group.open;
        writeNavState(next);
      });
    });
    window.addEventListener("pagehide", snapshotNavState);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") snapshotNavState();
    });
  }
  function markCurrent(){
    const current = normalizeDocumentPath(new URL(location.href).pathname);
    let currentLink = null;
    document.querySelectorAll(".nav-link[href]").forEach((link) => {
      link.removeAttribute("aria-current");
      const target = normalizeDocumentPath(new URL(link.getAttribute("href"), location.href).pathname);
      if (target === current) {
        currentLink = link;
        link.setAttribute("aria-current", "page");
        let parent = link.closest("details");
        while (parent) { parent.open = true; parent = parent.parentElement.closest("details"); }
      }
    });
    return currentLink;
  }
  function setupSidebarScrollMemory(currentLink){
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    const savedScroll = readSidebarScroll();
    requestAnimationFrame(() => {
      if (savedScroll !== null) sidebar.scrollTop = savedScroll;
      if (!currentLink) return;
      const sidebarRect = sidebar.getBoundingClientRect();
      const linkRect = currentLink.getBoundingClientRect();
      if (savedScroll === null || linkRect.top < sidebarRect.top || linkRect.bottom > sidebarRect.bottom) {
        sidebar.scrollTop = Math.max(0, currentLink.offsetTop - Math.round((sidebar.clientHeight - currentLink.offsetHeight) / 2));
      }
    });
    let scrollFrame = 0;
    sidebar.addEventListener("scroll", () => {
      if (scrollFrame) return;
      scrollFrame = requestAnimationFrame(() => {
        scrollFrame = 0;
        writeSidebarScroll(sidebar.scrollTop);
      });
    }, {passive: true});
    window.addEventListener("pagehide", () => writeSidebarScroll(sidebar.scrollTop));
  }
  function finishNavRestore(){
    requestAnimationFrame(() => {
      isRestoringNav = false;
      document.documentElement.removeAttribute("data-nav-restoring");
    });
  }
  function closeSearchOverlay(){
    const overlay = document.getElementById("searchOverlay");
    if (!overlay) return;
    overlay.hidden = true;
    document.body.classList.remove("is-search-open");
  }
  function isPlainNavigationClick(event, link){
    return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey && link.target !== "_blank";
  }
  function isGuideDocumentUrl(url){
    const path = url.pathname.toLowerCase();
    return url.origin === location.origin && (path.endsWith("/") || path.endsWith(".html") || path.endsWith(".htm"));
  }
  function rewriteArticleUrls(article, pageUrl){
    const attributes = [
      ["a[href]", "href"],
      ["img[src]", "src"],
      ["source[src]", "src"],
      ["video[src]", "src"],
      ["audio[src]", "src"]
    ];
    attributes.forEach(([selector, attribute]) => {
      article.querySelectorAll(selector).forEach((node) => {
        const value = node.getAttribute(attribute);
        if (!value || value.startsWith("#")) return;
        try { node.setAttribute(attribute, new URL(value, pageUrl).href); } catch (_) {}
      });
    });
  }
  async function replaceArticleFromUrl(url, options){
    const response = await fetch(url.href, {credentials: "same-origin"});
    if (!response.ok) throw new Error("문서를 불러올 수 없습니다.");
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const nextArticle = doc.querySelector("article.guide-content");
    const contentShell = document.querySelector("main.content-shell");
    if (!nextArticle || !contentShell) throw new Error("본문 영역을 찾을 수 없습니다.");
    rewriteArticleUrls(nextArticle, url);
    contentShell.replaceChildren(document.importNode(nextArticle, true));
    document.title = doc.title || document.title;
    if (options.push) history.pushState({}, "", url.href);
    markCurrent();
    closeSearchOverlay();
    window.scrollTo({top: 0, behavior: "auto"});
  }
  function setupPartialNavigation(){
    document.documentElement.dataset.partialNavigation = location.protocol === "file:" ? "fallback" : "enabled";
    if (location.protocol === "file:") return;
    document.addEventListener("click", (event) => {
      const link = event.target.closest ? event.target.closest("a[href]") : null;
      if (!link || !isPlainNavigationClick(event, link)) return;
      let url;
      try { url = new URL(link.getAttribute("href"), location.href); } catch (_) { return; }
      if (!isGuideDocumentUrl(url)) return;
      const currentWithoutHash = location.href.split("#")[0];
      const targetWithoutHash = url.href.split("#")[0];
      if (currentWithoutHash === targetWithoutHash) return;
      event.preventDefault();
      snapshotNavState();
      replaceArticleFromUrl(url, {push: true}).catch(() => { location.href = url.href; });
    }, true);
    window.addEventListener("popstate", () => {
      replaceArticleFromUrl(new URL(location.href), {push: false}).catch(() => location.reload());
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
      const body = String(item.body || "").replace(/\\s+/g, " ").trim();
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
  absolutizeShellLinks();
  document.documentElement.dataset.navRestoring = "1";
  setupNavGroups();
  const currentLink = markCurrent();
  setupSidebarScrollMemory(currentLink);
  finishNavRestore();
  setupSearch();
  setupPartialNavigation();
})();
""".strip(),
    )


def write_404(pages: list[Page]) -> None:
    placeholder = Page(source_path=Path("404"), title="페이지를 찾을 수 없습니다", slug="404-placeholder", version="미기재", edited_at="미기재")
    body = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>페이지를 찾을 수 없습니다 · AIMT Guide</title>
  <script>(function(){{document.documentElement.dataset.navRestoring="1";try{{var theme=localStorage.getItem("aimt-guide-theme");if(theme==="light"||theme==="dark")document.documentElement.dataset.theme=theme;if(localStorage.getItem("aimt-guide-sidebar-collapsed")==="1")document.documentElement.dataset.sidebar="collapsed";}}catch(_){{}}}})();</script>
  <style id="navRestoreStyle">:root[data-nav-restoring="1"] .nav-list{{visibility:hidden}}:root[data-nav-restoring="1"] .nav-caret{{transition:none}}</style>
  <link rel="stylesheet" href="guide/static/styles.css">
</head>
<body>
  <button id="sidebarExpand" class="sidebar-expand sidebar-toggle" type="button" aria-label="사이드바 열기" title="사이드바 열기">☰</button>
  <div id="searchOverlay" class="search-overlay" hidden>
    <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="searchTitle">
      <div class="search-header"><h2 id="searchTitle">문서 검색</h2><button id="searchClose" class="search-close" type="button" aria-label="검색 닫기" title="검색 닫기">×</button></div>
      <input id="guideSearch" class="search-input" type="search" placeholder="검색어 입력" autocomplete="off">
      <div id="searchResults" class="search-results" hidden></div>
    </section>
  </div>
  <div class="site-shell">
    <aside class="sidebar">
      <div class="brand-row"><a class="brand" href="guide/index.html">AIMT GUIDE</a><button id="searchOpen" class="sidebar-toggle" type="button" aria-label="문서 검색" title="문서 검색">⌕</button><button id="themeToggle" class="theme-toggle" type="button" aria-label="테마 변경" title="테마 변경">◐</button><button id="sidebarCollapse" class="sidebar-toggle" type="button" aria-label="사이드바 닫기" title="사이드바 닫기">←</button></div>
      
      <nav class="nav-list" aria-label="문서 목록">
{make_nav(pages, DIST_ROOT / "404.html")}
      </nav>
    </aside>
    <div id="sidebarResizer" class="sidebar-resizer" role="separator" aria-label="사이드바 너비 조절" aria-orientation="vertical" tabindex="0"></div>
    <main class="content-shell">
      <article class="guide-content">
        <h1>{html.escape(placeholder.title, quote=False)}</h1>
        <p>주소를 확인하거나 왼쪽 문서 목록에서 다시 선택해주세요.</p>
      </article>
    </main>
  </div>
  <script src="guide/static/main.js"></script>
</body>
</html>
"""
    write_text(DIST_ROOT / "404.html", body)


def write_pages_entrypoint() -> None:
    body = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=guide/">
  <title>AIMT Guide</title>
  <link rel="canonical" href="guide/">
  <script>location.replace("guide/" + location.search + location.hash);</script>
</head>
<body>
  <p><a href="guide/">AIMT Guide로 이동</a></p>
</body>
</html>
"""
    write_text(DIST_ROOT / "index.html", body)
    write_text(DIST_ROOT / ".nojekyll", "")


def migrate() -> list[Page]:
    pages, page_map = build_pages()
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    page_bodies: dict[Path, str] = {}
    for page in pages:
        body = extract_body_fragment(page, page_map)
        page_bodies[page.source_path] = body
        write_text(page.output_path, render_page(page, pages, body))
    write_static_assets()
    write_search_index(pages, page_bodies)
    write_404(pages)
    write_pages_entrypoint()
    return pages


def main() -> int:
    pages = migrate()
    print(f"ExportBlock migrated to dist: pages={len(pages)} assets={len(list(ASSET_ROOT.rglob('*'))) if ASSET_ROOT.exists() else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
