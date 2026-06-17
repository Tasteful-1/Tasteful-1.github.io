from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

HOST = "127.0.0.1"
PORT = 8776


def find_site_root() -> Path:
    current = Path(__file__).resolve().parents[1]
    if (current / "dist").exists() or (current / "ExportBlock").exists():
        return current
    return Path(__file__).resolve().parents[3] / "docs" / "guide-site"


SITE_ROOT = find_site_root()
DIST_ROOT = SITE_ROOT / "dist"
ARTICLE_RE = re.compile(r"(?is)<article\b[^>]*class=[\"'][^\"']*guide-content[^\"']*[\"'][^>]*>.*?</article>")
TITLE_RE = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")
NAV_RE = re.compile(r"(?is)(<nav\b[^>]*class=[\"'][^\"']*nav-list[^\"']*[\"'][^>]*>)(.*?)(</nav>)")
HREF_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)
DEPTH_RE = re.compile(r"data-depth=[\"'](\d+)[\"']", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def strip_tags(value: str) -> str:
    return html.unescape(TAG_RE.sub(" ", value)).strip()


def parse_title(text: str, fallback: str) -> str:
    match = TITLE_RE.search(text)
    return re.sub(r"\s+", " ", strip_tags(match.group(1))).strip() if match else fallback


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^0-9a-z가-힣_-]+", "-", value.strip().lower()).strip("-_")
    return re.sub(r"-{2,}", "-", slug) or "new-page"


def html_files(dist_root: Path) -> list[Path]:
    return sorted(path for path in dist_root.rglob("*.html") if path.name != "404.html")


def resolve_html_path(dist_root: Path, relative_path: str) -> Path:
    raw = unquote(relative_path).replace("\\", "/").lstrip("/")
    if raw.startswith("dist/"):
        raw = raw[5:]
    path = (dist_root / raw).resolve()
    try:
        path.relative_to(dist_root.resolve())
    except ValueError as exc:
        raise ValueError("dist 밖의 파일은 열 수 없습니다.") from exc
    if path.is_dir():
        path = path / "index.html"
    if path.suffix.lower() != ".html" or not path.exists():
        raise FileNotFoundError("HTML 파일을 찾을 수 없습니다.")
    return path


def get_href_target(dist_root: Path, html_path: Path, href: str) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme or href.startswith("#"):
        return None
    clean = unquote(parsed.path)
    if clean.startswith("/dist/"):
        path = dist_root / clean[6:]
    elif clean.startswith("/AIMT_Build/"):
        path = dist_root / clean[len("/AIMT_Build/"):]
    elif clean.startswith("/"):
        path = dist_root / clean.lstrip("/")
    else:
        path = html_path.parent / clean
    if path.suffix == "" or href.endswith("/"):
        path = path / "index.html"
    try:
        return path.resolve().relative_to(dist_root.resolve()).as_posix()
    except ValueError:
        return None


def relative_href(from_path: Path, to_relative: str, dist_root: Path = DIST_ROOT) -> str:
    to_path = dist_root / to_relative
    base_parts = from_path.parent.relative_to(dist_root).parts
    parts = [".."] * len(base_parts) + list(to_path.relative_to(dist_root).parts)
    return quote("/".join(parts), safe="/._-#%")


def get_nav_entries(dist_root: Path) -> list[dict[str, Any]]:
    index_path = dist_root / "guide" / "index.html"
    if not index_path.exists():
        return []
    match = NAV_RE.search(read_text(index_path))
    if not match:
        return []
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in match.group(2).splitlines():
        href = HREF_RE.search(line)
        if not href:
            continue
        target = get_href_target(dist_root, index_path, href.group(1))
        if not target or target in seen:
            continue
        depth = DEPTH_RE.search(line)
        entries.append({"path": target, "title": strip_tags(line), "depth": int(depth.group(1)) if depth else 0, "order": len(entries), "hasChildren": False})
        seen.add(target)
    for index, entry in enumerate(entries[:-1]):
        entry["hasChildren"] = int(entries[index + 1]["depth"]) > int(entry["depth"])
    return entries


def build_nav(entries: list[dict[str, Any]], html_path: Path, dist_root: Path = DIST_ROOT) -> str:
    lines: list[str] = []
    stack: list[int] = []
    for index, entry in enumerate(entries):
        depth = int(entry["depth"])
        next_depth = int(entries[index + 1]["depth"]) if index + 1 < len(entries) else -1
        while stack and stack[-1] >= depth:
            lines.append("</div></details>")
            stack.pop()
        title = html.escape(str(entry["title"]), quote=False)
        href = relative_href(html_path, str(entry["path"]), dist_root)
        anchor = f'<a class="nav-link" href="{href}" data-depth="{depth}">{title}</a>'
        if next_depth > depth:
            open_attr = " open" if depth == 0 else ""
            lines.append(f'<details class="nav-group" data-depth="{depth}"{open_attr}><summary><span class="nav-caret" aria-hidden="true"></span>{anchor}</summary><div class="nav-children">')
            stack.append(depth)
        else:
            lines.append(anchor)
    while stack:
        lines.append("</div></details>")
        stack.pop()
    return "\n".join(lines)


def rewrite_navs(dist_root: Path, entries: list[dict[str, Any]]) -> int:
    changed = 0
    for path in html_files(dist_root) + [dist_root / "404.html"]:
        if not path.exists():
            continue
        text = read_text(path)
        if not NAV_RE.search(text):
            continue
        nav = build_nav(entries, path, dist_root)
        write_text(path, NAV_RE.sub(lambda m: m.group(1) + "\n" + nav + "\n      " + m.group(3), text, count=1))
        changed += 1
    return changed


def list_files(dist_root: Path) -> list[dict[str, Any]]:
    entries = get_nav_entries(dist_root)
    meta = {entry["path"]: entry for entry in entries}
    order = {entry["path"]: int(entry["order"]) for entry in entries}
    files: list[dict[str, Any]] = []
    for path in sorted(dist_root.rglob("*.html"), key=lambda p: (order.get(p.relative_to(dist_root).as_posix(), 999999), p.relative_to(dist_root).as_posix())):
        rel = path.relative_to(dist_root).as_posix()
        if rel == "404.html":
            continue
        entry = meta.get(rel)
        text = read_text(path)
        files.append({"path": rel, "title": parse_title(text, path.parent.name), "updated": int(path.stat().st_mtime), "depth": int(entry.get("depth", 0)) if entry else 0, "inNav": bool(entry), "movable": bool(entry), "hasChildren": bool(entry.get("hasChildren", False)) if entry else False})
    return files


def extract_article(text: str) -> str:
    match = ARTICLE_RE.search(text)
    if not match:
        raise ValueError("article.guide-content를 찾지 못했습니다.")
    return match.group(0)


def replace_article(text: str, article: str) -> str:
    clean = re.sub(r"\s*contenteditable=[\"']true[\"']", "", article, flags=re.IGNORECASE)
    clean = clean.replace(" is-selected-image", "")
    return ARTICLE_RE.sub(clean, text, count=1)


def rebuild_search_index(dist_root: Path) -> None:
    items = []
    for item in list_files(dist_root):
        if not item["path"].startswith("guide/"):
            continue
        article = extract_article(read_text(dist_root / item["path"]))
        body = re.sub(r"\s+", " ", strip_tags(article))
        items.append({"title": item["title"], "url": relative_href(dist_root / "guide" / "index.html", item["path"], dist_root), "path": item["path"], "body": body})
    write_text(dist_root / "guide" / "search-index.json", json.dumps(items, ensure_ascii=False, indent=2))


def save_image(dist_root: Path, html_path: Path, filename: str, mime: str, data_url: str) -> dict[str, Any]:
    if mime not in IMAGE_EXT:
        raise ValueError("PNG/JPG/GIF/WEBP 이미지만 넣을 수 있습니다.")
    prefix = f"data:{mime};base64,"
    if not data_url.startswith(prefix):
        raise ValueError("이미지 데이터가 올바르지 않습니다.")
    stem = normalize_slug(Path(filename).stem)[:48] or "image"
    assets = dist_root / "guide" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    path = assets / f"{stem}{IMAGE_EXT[mime]}"
    index = 2
    while path.exists():
        path = assets / f"{stem}-{index}{IMAGE_EXT[mime]}"
        index += 1
    path.write_bytes(base64.b64decode(data_url[len(prefix):], validate=True))
    return {"ok": True, "path": path.relative_to(dist_root).as_posix(), "src": relative_href(html_path, path.relative_to(dist_root).as_posix(), dist_root)}


def reparent(dist_root: Path, source_path: str, parent_path: str) -> dict[str, Any]:
    source = resolve_html_path(dist_root, source_path).relative_to(dist_root).as_posix()
    parent = resolve_html_path(dist_root, parent_path).relative_to(dist_root).as_posix()
    entries = get_nav_entries(dist_root)
    source_index = next((i for i, e in enumerate(entries) if e["path"] == source), -1)
    parent_index = next((i for i, e in enumerate(entries) if e["path"] == parent), -1)
    if source_index < 0 or parent_index < 0 or source == parent:
        raise ValueError("목차에 있는 서로 다른 페이지끼리만 이동할 수 있습니다.")
    source_depth = int(entries[source_index]["depth"])
    end = source_index + 1
    while end < len(entries) and int(entries[end]["depth"]) > source_depth:
        end += 1
    if source_index <= parent_index < end:
        raise ValueError("묶음을 자기 하위 페이지 아래로 넣을 수 없습니다.")
    block = entries[source_index:end]
    del entries[source_index:end]
    if source_index < parent_index:
        parent_index -= len(block)
    delta = int(entries[parent_index]["depth"]) + 1 - source_depth
    for entry in block:
        entry["depth"] = int(entry["depth"]) + delta
    entries[parent_index + 1:parent_index + 1] = block
    changed = rewrite_navs(dist_root, entries)
    rebuild_search_index(dist_root)
    return {"ok": True, "changed": changed, "path": source, "parent": parent}

EDITOR_HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AIMT Guide Editor</title><style>
:root{--bg:#eef2f8;--panel:#fff;--ink:#182033;--muted:#647084;--line:#d8e0ee;--accent:#315bef;--soft:#edf3ff;--danger:#d92d20}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.app{display:grid;grid-template-columns:330px minmax(0,1fr);height:100vh}.side{overflow:auto;background:#fff;border-right:1px solid var(--line);padding:18px}.main{overflow:auto;padding:22px}.title{font-size:20px;font-weight:900;margin:0}.hint{font-size:12px;color:var(--muted)}.top{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}.btn{border:1px solid var(--line);background:#fff;border-radius:10px;padding:8px 10px;cursor:pointer}.btn.primary{border-color:var(--accent);background:var(--accent);color:#fff}.btn:disabled{opacity:.45}.filter{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:12px;margin:8px 0 12px}.file{display:block;width:100%;text-align:left;border:0;background:transparent;border-radius:12px;padding:8px 10px;margin:2px 0;cursor:pointer}.file:hover,.file.active{background:var(--soft)}.file.is-unlisted{opacity:.55}.file[draggable=true]{cursor:grab}.file.dragging{opacity:.45}.file.drop-child{box-shadow:inset 0 0 0 2px var(--accent);background:#e8efff}.file-title{display:block;font-weight:700}.file-path{display:block;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.file-tree-marker{display:inline-block;width:1.25em;color:var(--muted)}.file-tree-marker.is-toggle{cursor:pointer;color:var(--accent)}.editor-card{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:0 18px 40px rgba(22,34,56,.08);overflow:hidden}.toolbar{position:sticky;top:0;z-index:10;display:flex;gap:6px;flex-wrap:wrap;padding:12px;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.toolbar select{border:1px solid var(--line);border-radius:10px;padding:7px}.editor-frame{display:block;width:100%;height:64vh;border:0;background:#fff}.source-wrap{position:sticky;bottom:0;background:#fff;border-top:1px solid var(--line);padding:10px;z-index:8}.source{width:100%;min-height:170px;font-family:Consolas,monospace;font-size:12px;border:1px solid var(--line);border-radius:12px;padding:10px}.status{font-size:13px;color:var(--muted)}.status.error{color:var(--danger)}@media(max-width:900px){.app{display:block;height:auto}.side{border-right:0;border-bottom:1px solid var(--line)}.editor-frame{height:70vh}.toolbar{position:fixed;left:12px;right:12px;bottom:12px;top:auto;border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 30px rgba(0,0,0,.16)}}
</style></head><body><div class="app"><aside class="side"><h1 class="title">AIMT Guide Editor</h1><div class="hint">저장 대상: docs/guide-site/dist HTML</div><div class="top"><button class="btn" id="refreshButton">새로고침</button><button class="btn primary" id="newPageButton">새 페이지</button></div><input class="filter" id="filter" placeholder="목록 검색"><div id="fileList"></div></aside><main class="main"><div class="top"><button class="btn primary" id="saveButton" disabled>저장</button><button class="btn" id="openHtmlButton" disabled>현재 HTML 열기</button><span class="status" id="status">HTML 파일을 불러오는 중입니다.</span></div><section class="editor-card"><div class="toolbar"><select id="blockSelect"><option value="p">문단</option><option value="h1">제목1</option><option value="h2">제목2</option><option value="h3">제목3</option><option value="pre">코드블록</option><option value="blockquote">인용</option></select><button class="btn" data-cmd="bold">굵게</button><button class="btn" data-cmd="italic">기울임</button><button class="btn" data-cmd="underline">밑줄</button><button class="btn" data-cmd="insertUnorderedList">목록</button><button class="btn" data-cmd="insertOrderedList">번호</button><button class="btn" id="linkButton">링크</button><button class="btn" id="hrButton">구분선</button><button class="btn" id="imageButton">이미지</button><input id="imageInput" type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden></div><iframe class="editor-frame" id="editorFrame" title="guide editor"></iframe><details class="source-wrap"><summary>HTML 소스보기</summary><textarea class="source" id="sourceBox" spellcheck="false"></textarea></details></section></main></div><script>
const state={files:[],currentPath:'',draggedPath:'',collapsedPaths:new Set(),collapseReady:false,selectedImage:null};
const fileList=document.getElementById('fileList'),filter=document.getElementById('filter'),statusEl=document.getElementById('status'),frame=document.getElementById('editorFrame'),sourceBox=document.getElementById('sourceBox'),saveButton=document.getElementById('saveButton'),openHtmlButton=document.getElementById('openHtmlButton');
function showStatus(t,e=false){statusEl.textContent=t;statusEl.className='status'+(e?' error':'')}function showError(e){showStatus(e.message||String(e),true)}async function fetchJson(u,o){const r=await fetch(u,o);const p=await r.json();if(!r.ok)throw new Error(p.error||'요청 실패');return p}function formatTime(ts){return new Date(ts*1000).toLocaleString()}
async function loadFiles(){const p=await fetchJson('/api/files');state.files=p.files;initializeCollapsedPaths();renderFiles();showStatus('HTML 파일 '+state.files.length+'개를 불러왔습니다.')}function initializeCollapsedPaths(){if(state.collapseReady)return;state.files.forEach(f=>{if(f.hasChildren&&Number(f.depth||0)>=1)state.collapsedPaths.add(f.path)});state.collapseReady=true}
function toggleTreeNode(f,e){e.stopPropagation();if(!f.hasChildren)return;if(state.collapsedPaths.has(f.path))state.collapsedPaths.delete(f.path);else state.collapsedPaths.add(f.path);renderFiles()}function expandAncestors(path){const i=state.files.findIndex(f=>f.path===path);if(i<0)return;let childDepth=Number(state.files[i].depth||0);for(let c=i-1;c>=0;c--){const f=state.files[c],d=Number(f.depth||0);if(d<childDepth){state.collapsedPaths.delete(f.path);childDepth=d}if(childDepth<=0)break}}
function hiddenByCollapse(f,stack){const d=Number(f.depth||0);while(stack.length&&stack[stack.length-1].depth>=d)stack.pop();if(stack.length)return true;if(f.hasChildren&&state.collapsedPaths.has(f.path))stack.push({path:f.path,depth:d});return false}function canDrag(f,searching){if(!f||!f.inNav||!f.movable)return false;if(!f.hasChildren)return true;return !searching&&state.collapsedPaths.has(f.path)}
function renderFiles(){const q=filter.value.trim().toLowerCase();fileList.innerHTML='';const searching=q.length>0,stack=[];const matches=state.files.filter(f=>(f.path+' '+f.title).toLowerCase().includes(q)&&(searching||!hiddenByCollapse(f,stack)));for(const f of matches){const drag=canDrag(f,searching),b=document.createElement('button');b.type='button';b.className='file'+(f.path===state.currentPath?' active':'')+(!f.inNav?' is-unlisted':'');b.title=f.path+'\n'+formatTime(f.updated);b.dataset.path=f.path;b.dataset.inNav=f.inNav?'1':'0';b.dataset.movable=drag?'1':'0';b.draggable=drag;b.style.paddingLeft=(10+Math.min(Number(f.depth||0),6)*16)+'px';b.onclick=()=>loadFile(f.path);b.addEventListener('dragstart',dragStart);b.addEventListener('dragover',dragOver);b.addEventListener('dragleave',e=>e.currentTarget.classList.remove('drop-child'));b.addEventListener('drop',e=>dropFile(e,f).catch(showError));b.addEventListener('dragend',clearDrop);const title=document.createElement('span');title.className='file-title';const marker=document.createElement('span');marker.className='file-tree-marker';marker.textContent=f.hasChildren?(state.collapsedPaths.has(f.path)&&!searching?'▸':'▾'):(f.inNav?(drag?'↕':'·'):'·');if(f.hasChildren){marker.classList.add('is-toggle');marker.title=state.collapsedPaths.has(f.path)?'펼치기':'접기';marker.onclick=e=>toggleTreeNode(f,e)}title.append(marker,document.createTextNode(f.title));const p=document.createElement('span');p.className='file-path';p.textContent=f.path;b.append(title,p);fileList.appendChild(b)}if(!matches.length){const empty=document.createElement('div');empty.className='hint';empty.textContent='검색 결과가 없습니다.';fileList.appendChild(empty)}}
function clearDrop(){state.draggedPath='';fileList.querySelectorAll('.dragging,.drop-child').forEach(e=>e.classList.remove('dragging','drop-child'))}function dragStart(e){const b=e.currentTarget;if(b.dataset.movable!=='1'){e.preventDefault();return}state.draggedPath=b.dataset.path;b.classList.add('dragging');e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',state.draggedPath)}function dragOver(e){const b=e.currentTarget;if(!state.draggedPath||b.dataset.inNav!=='1'||b.dataset.path===state.draggedPath)return;e.preventDefault();b.classList.add('drop-child')}async function dropFile(e,target){if(!state.draggedPath||!target||target.path===state.draggedPath){clearDrop();return}e.preventDefault();const p=await fetchJson('/api/reparent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:state.draggedPath,parent:target.path})});await loadFiles();state.collapsedPaths.delete(target.path);renderFiles();clearDrop();showStatus('하위 페이지로 이동했습니다. 반영 파일: '+p.changed+'개')}
function doc(){return frame.contentDocument||frame.contentWindow.document}function styles(){return `<style>body{margin:0;padding:28px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65}.guide-content{outline:0;min-height:480px}.doc-version{font-size:13px;color:#647084}pre{padding:16px;overflow:auto;border-radius:14px;background:#101828;color:#e5e7eb}code{padding:.12em .35em;border-radius:6px;background:#eef2ff}blockquote{padding:12px 16px;border-left:4px solid #315bef;background:#eef3ff;border-radius:12px}img{max-width:100%;height:auto;border-radius:12px}.is-selected-image{outline:3px solid #315bef;outline-offset:3px}.image-tools{position:absolute;z-index:1000;display:flex;gap:4px;padding:6px;background:#fff;border:1px solid #d8e0ee;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.18)}.image-tools button{border:1px solid #d8e0ee;background:#fff;border-radius:8px;padding:5px 7px}.resize-handle{position:absolute;z-index:999;width:12px;height:12px;background:#315bef;border:2px solid #fff;border-radius:999px}</style>`}
function setArticle(a){frame.srcdoc=`<!doctype html><html><head>${styles()}</head><body>${a}</body></html>`;sourceBox.value=a;frame.onload=setupFrame}function setupFrame(){const d=doc(),a=d.querySelector('.guide-content');if(!a)return;a.contentEditable='true';a.addEventListener('input',()=>sourceBox.value=getArticle());d.addEventListener('click',e=>{if(e.target&&e.target.tagName==='IMG')selectImage(e.target);else clearImage()});d.addEventListener('paste',e=>{const f=[...(e.clipboardData?.files||[])].find(x=>x.type.startsWith('image/'));if(f){e.preventDefault();insertImage(f).catch(showError)}});a.addEventListener('dragover',e=>{if([...(e.dataTransfer?.files||[])].some(f=>f.type.startsWith('image/')))e.preventDefault()});a.addEventListener('drop',e=>{const f=[...(e.dataTransfer?.files||[])].find(x=>x.type.startsWith('image/'));if(f){e.preventDefault();insertImage(f).catch(showError)}})}
function getArticle(){const d=doc();d.querySelectorAll('.image-tools,.resize-handle').forEach(e=>e.remove());d.querySelectorAll('.is-selected-image').forEach(e=>e.classList.remove('is-selected-image'));return d.querySelector('.guide-content')?.outerHTML||sourceBox.value}async function loadFile(path){const p=await fetchJson('/api/file?path='+encodeURIComponent(path));state.currentPath=p.path;setArticle(p.article);saveButton.disabled=false;openHtmlButton.disabled=false;expandAncestors(path);renderFiles();showStatus('열림: '+p.path)}async function saveCurrent(){if(!state.currentPath)return;const article=getArticle();await fetchJson('/api/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:state.currentPath,article})});sourceBox.value=article;showStatus('저장했습니다.');await loadFiles()}
function exec(cmd,val=null){doc().execCommand(cmd,false,val);sourceBox.value=getArticle();frame.contentWindow.focus()}document.querySelectorAll('[data-cmd]').forEach(b=>b.onclick=()=>exec(b.dataset.cmd));document.getElementById('blockSelect').onchange=e=>exec('formatBlock',e.target.value);document.getElementById('linkButton').onclick=()=>{const u=prompt('링크 주소');if(u)exec('createLink',u)};document.getElementById('hrButton').onclick=()=>exec('insertHorizontalRule');document.getElementById('imageButton').onclick=()=>document.getElementById('imageInput').click();document.getElementById('imageInput').onchange=e=>{const f=e.target.files[0];if(f)insertImage(f).catch(showError);e.target.value=''};
function fileData(f){return new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(f)})}async function insertImage(file){if(!state.currentPath)throw new Error('먼저 문서를 열어주세요.');const dataUrl=await fileData(file);const p=await fetchJson('/api/asset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:state.currentPath,filename:file.name,mime:file.type,dataUrl})});exec('insertHTML',`<p><img src="${p.src}" alt=""></p>`);showStatus('이미지를 넣었습니다: '+p.path)}
function clearImage(){const d=doc();d.querySelectorAll('.image-tools,.resize-handle').forEach(e=>e.remove());d.querySelectorAll('.is-selected-image').forEach(e=>e.classList.remove('is-selected-image'));state.selectedImage=null}function selectImage(img){clearImage();state.selectedImage=img;img.classList.add('is-selected-image');const d=doc(),r=img.getBoundingClientRect(),sx=d.defaultView.scrollX,sy=d.defaultView.scrollY;const tools=d.createElement('div');tools.className='image-tools';tools.style.left=(r.left+sx)+'px';tools.style.top=(r.top+sy-44)+'px';[['왼쪽','left'],['중앙','center'],['오른쪽','right'],['50%','50'],['100%','100']].forEach(([label,val])=>{const b=d.createElement('button');b.textContent=label;b.onclick=()=>imageAction(val);tools.appendChild(b)});d.body.appendChild(tools);const h=d.createElement('span');h.className='resize-handle';h.style.left=(r.right+sx-6)+'px';h.style.top=(r.bottom+sy-6)+'px';h.onmousedown=e=>startResize(e,img);d.body.appendChild(h)}function imageAction(v){const img=state.selectedImage;if(!img)return;if(v==='left'||v==='center'||v==='right'){img.style.display='block';img.style.marginLeft=v==='left'?'0':'auto';img.style.marginRight=v==='right'?'0':'auto'}else{img.style.width=v+'%';img.style.height='auto'}sourceBox.value=getArticle();selectImage(img)}function startResize(e,img){e.preventDefault();const w=doc().defaultView,sx=e.clientX,sy=e.clientY,sw=img.getBoundingClientRect().width,sh=img.getBoundingClientRect().height;function mv(ev){img.style.width=Math.max(24,Math.round(sw+ev.clientX-sx))+'px';img.style.height=Math.max(24,Math.round(sh+ev.clientY-sy))+'px'}function up(){w.removeEventListener('mousemove',mv);w.removeEventListener('mouseup',up);sourceBox.value=getArticle();selectImage(img)}w.addEventListener('mousemove',mv);w.addEventListener('mouseup',up)}
sourceBox.addEventListener('input',()=>{doc().body.innerHTML=sourceBox.value;setupFrame()});saveButton.onclick=()=>saveCurrent().catch(showError);document.getElementById('refreshButton').onclick=()=>loadFiles().catch(showError);filter.oninput=renderFiles;openHtmlButton.onclick=()=>{if(state.currentPath)window.open('/dist/'+state.currentPath,'_blank')};document.getElementById('newPageButton').onclick=async()=>{const title=prompt('새 페이지 제목');if(!title)return;const slug=prompt('주소 slug',title.toLowerCase().replace(/\s+/g,'-'))||title;const p=await fetchJson('/api/page',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,slug})});state.collapseReady=false;await loadFiles();await loadFile(p.path)};loadFiles().catch(showError);
</script></body></html>'''

def render_new_page(title: str, relative_path: str, entries: list[dict[str, Any]], dist_root: Path = DIST_ROOT) -> str:
    html_path = dist_root / relative_path
    safe = html.escape(title, quote=False)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe} · AIMT Guide</title><script>(function(){{try{{var theme=localStorage.getItem("aimt-guide-theme");if(theme==="light"||theme==="dark")document.documentElement.dataset.theme=theme;if(localStorage.getItem("aimt-guide-sidebar-collapsed")==="1")document.documentElement.dataset.sidebar="collapsed";}}catch(_){{}}}})();</script><link rel="stylesheet" href="{relative_href(html_path, 'guide/static/styles.css', dist_root)}"></head><body>  <div id="searchOverlay" class="search-overlay" hidden>    <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="searchTitle">      <div class="search-header"><h2 id="searchTitle">문서 검색</h2><button id="searchClose" class="search-close" type="button" aria-label="검색 닫기" title="검색 닫기">×</button></div>      <input id="guideSearch" class="search-input" type="search" placeholder="검색어 입력" autocomplete="off">      <div id="searchResults" class="search-results" hidden></div>    </section>  </div><button id="sidebarExpand" class="sidebar-expand sidebar-toggle" type="button" aria-label="사이드바 열기" title="사이드바 열기">☰</button><div class="site-shell"><aside class="sidebar"><div class="brand-row"><a class="brand" href="{relative_href(html_path, 'guide/index.html', dist_root)}">AIMT GUIDE</a><button id="searchOpen" class="sidebar-toggle" type="button" aria-label="문서 검색" title="문서 검색">⌕</button><button id="themeToggle" class="theme-toggle" type="button" aria-label="테마 변경" title="테마 변경">◐</button><button id="sidebarCollapse" class="sidebar-toggle" type="button" aria-label="사이드바 닫기" title="사이드바 닫기">←</button></div><nav class="nav-list" aria-label="문서 목록">
{build_nav(entries, html_path, dist_root)}
      </nav></aside><div id="sidebarResizer" class="sidebar-resizer" role="separator" aria-label="사이드바 너비 조절" aria-orientation="vertical" tabindex="0"></div><main class="content-shell"><article class="guide-content"><h1>{safe}</h1><p class="doc-version">작성 당시 버전: 미기재</p><p>새 문서입니다. 본문을 작성해주세요.</p></article></main></div><script src="{relative_href(html_path, 'guide/static/main.js', dist_root)}"></script></body></html>'''


def create_page(dist_root: Path, title: str, slug: str) -> dict[str, Any]:
    clean_title = title.strip() or "새 문서"
    clean_slug = normalize_slug(slug or clean_title)
    relative = f"guide/{clean_slug}/index.html"
    path = dist_root / relative
    if path.exists():
        raise ValueError("이미 같은 주소의 문서가 있습니다.")
    entries = get_nav_entries(dist_root)
    entries.insert(1 if entries else 0, {"path": relative, "title": clean_title, "depth": 1, "order": 0, "hasChildren": False})
    write_text(path, render_new_page(clean_title, relative, entries, dist_root))
    rewrite_navs(dist_root, entries)
    rebuild_search_index(dist_root)
    return {"ok": True, "path": relative, "title": clean_title}


def json_response(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes, str]:
    return status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8"


def text_response(text: str, content_type: str = "text/html; charset=utf-8", status: int = 200) -> tuple[int, bytes, str]:
    return status, text.encode("utf-8"), content_type


def content_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


class GuideEditorHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *args: Any) -> None:
        return

    def send_payload(self, response: tuple[int, bytes, str]) -> None:
        status, body, ctype = response
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            match parsed.path:
                case "/":
                    self.send_payload(text_response(EDITOR_HTML))
                case "/api/files":
                    self.send_payload(json_response({"files": list_files(DIST_ROOT)}))
                case "/api/file":
                    self.send_payload(self.get_file(parsed.query))
                case path if path.startswith("/dist/"):
                    self.send_payload(self.get_static(path))
                case _:
                    self.send_payload(json_response({"error": "지원하지 않는 경로입니다."}, 404))
        except Exception as exc:
            self.send_payload(json_response({"error": str(exc)}, 500))

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            match urlparse(self.path).path:
                case "/api/file":
                    self.send_payload(self.post_file(payload))
                case "/api/asset":
                    html_path = resolve_html_path(DIST_ROOT, str(payload.get("path", "")))
                    self.send_payload(json_response(save_image(DIST_ROOT, html_path, str(payload.get("filename", "")), str(payload.get("mime", "")), str(payload.get("dataUrl", "")))))
                case "/api/page":
                    self.send_payload(json_response(create_page(DIST_ROOT, str(payload.get("title", "")), str(payload.get("slug", "")))))
                case "/api/reparent":
                    self.send_payload(json_response(reparent(DIST_ROOT, str(payload.get("source", "")), str(payload.get("parent", "")))))
                case _:
                    self.send_payload(json_response({"error": "지원하지 않는 경로입니다."}, 404))
        except Exception as exc:
            self.send_payload(json_response({"error": str(exc)}, 400))

    def get_file(self, query: str) -> tuple[int, bytes, str]:
        path = resolve_html_path(DIST_ROOT, parse_qs(query).get("path", [""])[0])
        text = read_text(path)
        return json_response({"path": path.relative_to(DIST_ROOT).as_posix(), "title": parse_title(text, path.stem), "article": extract_article(text)})

    def get_static(self, raw_path: str) -> tuple[int, bytes, str]:
        relative = unquote(raw_path.removeprefix("/dist/")).replace("\\", "/")
        path = (DIST_ROOT / relative).resolve()
        try:
            path.relative_to(DIST_ROOT.resolve())
        except ValueError as exc:
            raise ValueError("dist 밖의 파일은 열 수 없습니다.") from exc
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            return text_response("Not Found", "text/plain; charset=utf-8", 404)
        return 200, path.read_bytes(), content_type(path)

    def post_file(self, payload: dict[str, Any]) -> tuple[int, bytes, str]:
        path = resolve_html_path(DIST_ROOT, str(payload.get("path", "")))
        write_text(path, replace_article(read_text(path), str(payload.get("article", ""))))
        rebuild_search_index(DIST_ROOT)
        return json_response({"ok": True, "path": path.relative_to(DIST_ROOT).as_posix()})


def main() -> int:
    if not DIST_ROOT.exists():
        raise SystemExit("docs/guide-site/dist가 없습니다. rebuild_recovery_dist.py를 먼저 실행해주세요.")
    server = ThreadingHTTPServer((HOST, PORT), GuideEditorHandler)
    print(f"AIMT Guide Editor: http://{HOST}:{PORT}/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
