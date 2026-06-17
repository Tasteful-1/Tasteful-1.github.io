from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

def find_site_root() -> Path:
    current = Path(__file__).resolve().parents[1]
    if (current / "dist").exists() or (current / "ExportBlock").exists():
        return current
    return Path(__file__).resolve().parents[3] / "docs" / "guide-site"


SITE_ROOT = find_site_root()
DIST_ROOT = SITE_ROOT / "dist"
GUIDE_ROOT = DIST_ROOT / "guide"
STATIC_ROOT = GUIDE_ROOT / "static"


@dataclass(frozen=True)
class PageSpec:
    title: str
    slug: str
    depth: int
    body: str
    version: str = "복구본"

    @property
    def path(self) -> Path:
        return GUIDE_ROOT / self.slug / "index.html" if self.slug else GUIDE_ROOT / "index.html"

    @property
    def relative(self) -> str:
        return self.path.relative_to(DIST_ROOT).as_posix()


PAGES: list[PageSpec] = [
    PageSpec("AIMT GUIDE", "", 0, """
<p>이 페이지는 손실된 guide-site를 가능한 범위에서 복구한 홈입니다.</p>
<p>기존 165개 HTML 원문은 현재 로컬/Git/Pages에서 원본을 찾지 못해 완전 복구하지 못했습니다. 대신 편집기, 배포 구조, 검색, 트리 목차, 주요 문서 골격을 다시 세웠습니다.</p>
<p><strong>확인 필요:</strong> 각 문서의 실제 본문은 에디터에서 다시 채워 넣어야 합니다.</p>
"""),
    PageSpec("RPG MAKER MVMZ 개정1", "rpg-maker-mvmz-개정1", 1, "<p>MVMZ 게임 번역 작업의 시작 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("RPG MAKER VXVXA 개정1", "rpg-maker-vxvxa-개정1", 1, "<p>VXVXA 게임 번역 작업의 시작 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("WOLF RPG Editor", "wolf-rpg-editor", 1, "<p>WOLF RPG Editor 게임 작업 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("TyranoBuilder/TyranoScript 개정1", "tyranobuilder-tyranoscript-개정1", 1, "<p>Tyrano 계열 게임 작업 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("LiveMaker", "livemaker", 1, "<p>LiveMaker 게임 작업 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("SRPG Studio", "srpg-studio", 1, "<p>SRPG Studio 게임 작업 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("세이브 에디터", "save-editor", 1, "<p>세이브 파일을 열고 수정한 뒤 백업/복원하는 사용자용 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("상단부", "상단부", 1, "<p>상단부 메뉴 설명 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("설정", "설정", 2, "<p>설정 화면 문서 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("AI-MODEL", "ai-model", 3, "<p>AI 모델 선택과 변경 기준을 설명하는 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("API KEY 설정", "api-key-설정", 3, "<p>API 키 입력과 오류 확인 흐름을 설명하는 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("401 Block Unit for Consistency/Duplicate", "401-block-unit-for-consistency-duplicate", 3, "<p>401 대화 블럭 단위 설정 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("하단부", "하단부", 1, "<p>하단부 작업 영역 설명 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("도구", "도구", 2, "<p>도구 탭 문서 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("MVMZ", "mvmz", 3, "<p>MVMZ 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("Data 복호화", "data-복호화", 4, "<p>Data 복호화 사용 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("프로젝트 변환", "프로젝트-변환", 4, "<p>프로젝트 변환 사용 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("VXVXA", "vxvxa", 3, "<p>VXVXA 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("WOLF", "wolf", 3, "<p>WOLF 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("언팩/리팩", "wolf-unpack-repack", 4, "<p>WOLF 압축 해제/다시 묶기 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("RAW/파일명 치환", "wolf-raw-filename", 4, "<p>WOLF 원본 정보와 파일명 치환 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("EXE 패치", "wolf-exe-patch", 4, "<p>WOLF 실행 파일 패치 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("CTF", "ctf", 3, "<p>CTF 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("CTF 처음부터 끝까지", "ctf-처음부터-끝까지", 4, "<p>CTF 프로젝트 지정, 추출, 번역, 적용 흐름 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("CTF 이미지가 깨질 때", "ctf-이미지가-깨질-때", 4, "<p>CTF 이미지 표시/적용 문제 해결 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("Tyrano", "tyrano", 3, "<p>Tyrano 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("Kirikiri", "kirikiri", 3, "<p>Kirikiri 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("PGMMV", "pgmmv", 3, "<p>PGMMV 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("Electron", "electron", 3, "<p>Electron 도구 묶음입니다. 원문 복구 필요.</p>"),
    PageSpec("퀵슬롯", "퀵슬롯", 2, "<p>퀵슬롯 사용 문서입니다. 원문 복구 필요.</p>"),
    PageSpec("RPGMAKER 명령코드 정리 작성 예정", "rpgmaker-명령코드-정리-작성-예정", 1, "<p>RPG Maker 명령 코드 정리 예정 문서입니다. 원문 복구 필요.</p>"),
]


def relative_href(from_path: Path, to_path: Path) -> str:
    rel = to_path.relative_to(DIST_ROOT)
    start = from_path.parent.relative_to(DIST_ROOT)
    value = Path(".") if str(start) == "." else start
    href = Path(*([".."] * len(value.parts))) / rel
    return quote(href.as_posix(), safe="/._-#%")


def make_nav(from_path: Path) -> str:
    lines: list[str] = []
    stack: list[int] = []
    for index, page in enumerate(PAGES):
        next_depth = PAGES[index + 1].depth if index + 1 < len(PAGES) else -1
        while stack and stack[-1] >= page.depth:
            lines.append("</div></details>")
            stack.pop()
        href = relative_href(from_path, page.path)
        title = html.escape(page.title, quote=False)
        anchor = f'<a class="nav-link" href="{href}" data-depth="{page.depth}">{title}</a>'
        if next_depth > page.depth:
            open_attr = " open" if page.depth == 0 else ""
            lines.append(f'<details class="nav-group" data-depth="{page.depth}"{open_attr}><summary>{anchor}</summary><div class="nav-children">')
            stack.append(page.depth)
        else:
            lines.append(anchor)
    while stack:
        lines.append("</div></details>")
        stack.pop()
    return "\n".join(lines)


def page_body(page: PageSpec) -> str:
    version = html.escape(page.version, quote=False)
    return f"""
<article class="guide-content">
  <h1>{html.escape(page.title, quote=False)}</h1>
  <p class="doc-version">작성 당시 버전: {version}</p>
  {page.body.strip()}
</article>
""".strip()


def render_page(page: PageSpec) -> str:
    path = page.path
    css_href = relative_href(path, STATIC_ROOT / "styles.css")
    js_href = relative_href(path, STATIC_ROOT / "main.js")
    home_href = relative_href(path, GUIDE_ROOT / "index.html")
    nav = make_nav(path)
    title = html.escape(page.title, quote=False)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · AIMT Guide</title>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
  <div id="searchOverlay" class="search-overlay" hidden>
    <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="searchTitle">
      <div class="search-header"><h2 id="searchTitle">문서 검색</h2><button id="searchClose" class="search-close" type="button" aria-label="검색 닫기" title="검색 닫기">×</button></div>
      <input id="guideSearch" class="search-input" type="search" placeholder="검색어 입력" autocomplete="off">
      <div id="searchResults" class="search-results" hidden></div>
    </section>
  </div>
  <div class="site-shell">
    <aside class="sidebar">
      <div class="brand-row"><a class="brand" href="{home_href}">AIMT GUIDE</a><button id="searchOpen" class="search-open" type="button" aria-label="문서 검색" title="문서 검색">⌕</button></div>
      <nav class="nav-list" aria-label="문서 목록">
{nav}
      </nav>
    </aside>
    <main class="content-shell">
      {page_body(page)}
    </main>
  </div>
  <script src="{js_href}"></script>
</body>
</html>
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def build_search_index() -> None:
    entries = []
    for page in PAGES:
        entries.append(
            {
                "title": page.title,
                "url": relative_href(GUIDE_ROOT / "index.html", page.path),
                "path": page.relative,
                "body": plain_text(page.body),
            }
        )
    write_text(GUIDE_ROOT / "search-index.json", json.dumps(entries, ensure_ascii=False, indent=2))


def write_static_assets() -> None:
    write_text(
        STATIC_ROOT / "styles.css",
        """
:root{--bg:#f4f6fb;--panel:#fff;--ink:#172033;--muted:#6b7280;--line:#dce2ef;--accent:#315bef;--soft:#eef3ff;--code:#101828}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65}.site-shell{display:grid;grid-template-columns:310px minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;overflow:auto;padding:22px 18px;background:#fff;border-right:1px solid var(--line)}.brand-row{display:flex;align-items:center;gap:10px;margin-bottom:18px}.brand{min-width:0;flex:1;color:var(--ink);font-weight:900;text-decoration:none;letter-spacing:.03em}.search-open,.search-close{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--muted);font:700 15px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;cursor:pointer}.search-open:hover,.search-close:hover{background:var(--soft);color:var(--accent)}.search-overlay{position:fixed;inset:0;z-index:80;display:grid;place-items:start center;padding:72px 20px 24px;background:rgba(15,20,32,.42)}.search-overlay[hidden]{display:none}.search-dialog{width:min(760px,100%);max-height:min(760px,calc(100vh - 96px));display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:0 24px 80px rgba(0,0,0,.24)}.search-header{display:flex;align-items:center;gap:12px;padding:18px 18px 12px;border-bottom:1px solid var(--line)}.search-header h2{flex:1;margin:0;border:0;padding:0;font-size:18px}.search-input{width:calc(100% - 36px);margin:16px 18px 10px;padding:12px 14px;border:1px solid var(--line);border-radius:12px}.search-results{display:block;overflow:auto;margin:0;padding:8px 18px 18px}.search-results a{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 10px;margin:4px 0;padding:10px 12px;border-radius:12px;color:var(--ink);text-decoration:none}.search-results a:hover{background:var(--soft)}.search-badge{display:inline-flex;align-items:center;height:22px;padding:0 7px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:12px;font-weight:700}.search-empty{padding:28px 8px;color:var(--muted);text-align:center}.nav-list{font-size:14px}.nav-link{display:block;margin:2px 0;padding:7px 9px;border-radius:10px;color:#26324a;text-decoration:none}.nav-link:hover,.nav-link[aria-current="page"]{background:var(--soft);color:var(--accent)}.nav-group>summary{list-style:none;cursor:pointer}.nav-group>summary::-webkit-details-marker{display:none}.nav-group>summary:before{content:"▸";display:inline-block;width:1.2em;color:var(--muted)}.nav-group[open]>summary:before{content:"▾"}.nav-children{margin-left:12px;padding-left:8px;border-left:1px solid var(--line)}.content-shell{padding:42px min(7vw,72px)}.guide-content{max-width:980px;margin:0 auto;padding:42px;background:var(--panel);border:1px solid var(--line);border-radius:24px;box-shadow:0 18px 45px rgba(31,41,55,.08)}h1{font-size:34px;line-height:1.2;margin:0 0 6px}h2{margin-top:38px;border-bottom:1px solid var(--line);padding-bottom:6px}.doc-version{margin:0 0 28px;color:var(--muted);font-size:13px}code{padding:.12em .35em;border-radius:6px;background:#eef2ff;color:#243b8f}pre{padding:16px;overflow:auto;border-radius:16px;background:var(--code);color:#e5e7eb}blockquote{margin:20px 0;padding:12px 18px;border-left:4px solid var(--accent);background:var(--soft);border-radius:12px}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid var(--line);padding:8px 10px}img{max-width:100%;height:auto;border-radius:12px}.image-marker{padding:10px 12px;border:1px dashed var(--accent);background:var(--soft);border-radius:12px;color:#1d3ed6;font-weight:700}@media(max-width:900px){.site-shell{display:block}.sidebar{position:relative;height:auto}.content-shell{padding:18px}.guide-content{padding:24px;border-radius:18px}}
""".strip(),
    )
    write_text(
        STATIC_ROOT / "main.js",
        """
(function(){
  const normalize = (value) => String(value || "").normalize("NFKC").toLowerCase().replace(/[\\s_\\-/.]+/g, " ").trim();
  const compact = (value) => normalize(value).replace(/ /g, "");
  function markCurrent(){
    const current = new URL(location.href).pathname.replace(/\\/index\\.html$/, "/");
    document.querySelectorAll(".nav-link[href]").forEach((link) => {
      const target = new URL(link.getAttribute("href"), location.href).pathname.replace(/\\/index\\.html$/, "/");
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
    const closeButton = document.getElementById("searchClose");
    const input = document.getElementById("guideSearch");
    const results = document.getElementById("searchResults");
    const script = document.currentScript;
    if (!openButton || !overlay || !closeButton || !input || !results || !script) return;
    let index = [];
    try { index = await fetch(new URL("../search-index.json", script.src)).then((res) => res.json()); } catch (_) { return; }
    function closeSearch(){ overlay.hidden = true; openButton.focus(); }
    function openSearch(){ overlay.hidden = false; input.focus(); input.select(); renderSearchResults(); }
    function badge(text){ const node = document.createElement("span"); node.className = "search-badge"; node.textContent = text; return node; }
    function renderSearchResults(){
      const query = normalize(input.value);
      const compactQuery = compact(input.value);
      results.innerHTML = "";
      if (!query) { const empty = document.createElement("div"); empty.className = "search-empty"; empty.textContent = "검색어를 입력하세요."; results.appendChild(empty); return; }
      const tokens = query.split(" ").filter(Boolean);
      const matches = index.map((item) => {
        const title = normalize(item.title), body = normalize(item.body), tightTitle = compact(item.title), tightBody = compact(item.body);
        const titleMatched = title.includes(query) || tightTitle.includes(compactQuery) || tokens.some((token) => title.includes(token) || tightTitle.includes(token));
        const bodyMatched = body.includes(query) || tightBody.includes(compactQuery) || tokens.some((token) => body.includes(token) || tightBody.includes(token));
        return {item, titleMatched, bodyMatched, score: (titleMatched ? 10 : 0) + (bodyMatched ? 4 : 0)};
      }).filter((row) => row.score > 0).sort((a,b) => b.score - a.score).slice(0, 20);
      if (!matches.length) { const empty = document.createElement("div"); empty.className = "search-empty"; empty.textContent = "검색 결과가 없습니다."; results.appendChild(empty); return; }
      for (const row of matches) {
        const a = document.createElement("a");
        a.href = new URL(row.item.url, new URL("..", script.src)).toString();
        a.append(document.createTextNode(row.item.title));
        const badges = document.createElement("span");
        if (row.titleMatched) badges.appendChild(badge("제목"));
        if (row.bodyMatched) badges.appendChild(badge("내용"));
        a.appendChild(badges);
        results.appendChild(a);
      }
    }
    openButton.addEventListener("click", openSearch);
    closeButton.addEventListener("click", closeSearch);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) closeSearch(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !overlay.hidden) closeSearch(); });
    input.addEventListener("input", renderSearchResults);
  }  markCurrent();
  setupSearch();
})();
""".strip(),
    )


def build() -> None:
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    for page in PAGES:
        write_text(page.path, render_page(page))
    write_static_assets()
    build_search_index()
    not_found = render_page(PageSpec("페이지를 찾을 수 없습니다", "404-placeholder", 0, "<p>주소를 확인하거나 왼쪽 문서 목록에서 다시 선택해주세요.</p>"))
    write_text(DIST_ROOT / "404.html", not_found.replace("../../guide/", "guide/"))


if __name__ == "__main__":
    build()
    print(f"Recovered guide dist: pages={len(PAGES)}")

