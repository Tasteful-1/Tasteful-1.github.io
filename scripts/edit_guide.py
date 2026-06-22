from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

HOST = "127.0.0.1"
PORT = 8776
DOC_VERSION = "문서 기준: AIMT PRO 1.13 계열"

GROUP_PAGES = {
    "guide/index.html",
    "guide/basic-workflow/index.html",
    "guide/engine-guides/index.html",
    "guide/features/index.html",
    "guide/troubleshooting/index.html",
    "guide/advanced-reference/index.html",
}

FEATURE_SUBGROUP_PAGES = {
    "guide/features-screen/index.html",
    "guide/퀵슬롯/index.html",
}

SETTING_REFERENCE_GROUP_PAGES = set()

EXTERNAL_REFERENCE_PAGES = {
    "guide/외부-유틸리티/index.html",
    "guide/제공자별-참고-링크/index.html",
}

EXCLUDE_FROM_NAV_PATHS = {
    "guide/start/index.html",
    "guide/engine-guides/index.html",
    "guide/features/index.html",
    "guide/troubleshooting/index.html",
    "guide/advanced-reference/index.html",
    "guide/advanced-regex-rules/index.html",
    "guide/advanced-mvmz-options/index.html",
    "guide/advanced-file-formats/index.html",
    "guide/advanced-ai-local/index.html",
    "guide/mvmz/index.html",
    "guide/vxvxa/index.html",
    "guide/wolf/index.html",
    "guide/ctf/index.html",
    "guide/tyrano/index.html",
    "guide/kirikiri/index.html",
    "guide/pgmmv/index.html",
    "guide/electron/index.html",
    "guide/features-workspace-tools/index.html",
    "guide/features-engine-tools/index.html",
    "guide/features-external-tools/index.html",
    "guide/features-settings/index.html",
    "guide/features-quickslot/index.html",
    "guide/용어사전/index.html",
    "guide/winmerge-check/index.html",
}

STRUCTURE_MANAGED_PATHS = GROUP_PAGES | FEATURE_SUBGROUP_PAGES | SETTING_REFERENCE_GROUP_PAGES | EXTERNAL_REFERENCE_PAGES
DEFAULT_NEW_PAGE_PARENT = "guide/features-screen/index.html"


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
NAV_LINK_RE = re.compile(r"(?is)<a\b(?P<attrs>[^>]*class=[\"'][^\"']*\bnav-link\b[^\"']*[\"'][^>]*)>(?P<title>.*?)</a>")
HREF_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)
DEPTH_RE = re.compile(r"data-depth=[\"'](\d+)[\"']", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}


class NavEntryParser(HTMLParser):
    """Parse the rendered guide navigation into editor tree entries.

    Expected failures:
        Invalid or partial HTML may omit entries, but parsing should not raise for
        ordinary guide pages.
    """

    def __init__(self, dist_root: Path, index_path: Path, dedupe: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.dist_root = dist_root
        self.index_path = index_path
        self.dedupe = dedupe
        self.entries: list[dict[str, Any]] = []
        self.seen: set[str] = set()
        self.details_stack: list[dict[str, str]] = []
        self.in_summary_depth = 0
        self.current_link: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name.lower(): value or "" for name, value in attrs}
        if tag == "details" and "nav-group" in attr.get("class", "").split():
            self.details_stack.append({"key": attr.get("data-nav-key", ""), "depth": attr.get("data-depth", "")})
            return
        if tag == "summary":
            self.in_summary_depth += 1
            return
        if tag not in {"a", "span"} or "nav-link" not in attr.get("class", "").split():
            return
        self.current_link = {"tag": tag, "attrs": attr, "text": []}

    def handle_endtag(self, tag: str) -> None:
        if self.current_link and tag == self.current_link["tag"]:
            self._finish_link()
            self.current_link = None
            return
        if tag == "summary" and self.in_summary_depth:
            self.in_summary_depth -= 1
            return
        if tag == "details" and self.details_stack:
            self.details_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.current_link:
            self.current_link["text"].append(data)

    def _finish_link(self) -> None:
        link = self.current_link
        if not link:
            return
        attrs: dict[str, str] = link["attrs"]
        title = re.sub(r"\s+", " ", "".join(link["text"])).strip()
        if not title:
            return
        details = self.details_stack[-1] if self.details_stack and self.in_summary_depth else {}
        href = attrs.get("href", "")
        target = get_href_target(self.dist_root, self.index_path, href) if href else None
        virtual = not bool(target)
        path = target or details.get("key", "")
        if not path:
            return
        if not virtual and is_excluded_path(path):
            return
        if self.dedupe and path in self.seen:
            return
        raw_depth = attrs.get("data-depth") or details.get("depth") or "0"
        try:
            depth = int(raw_depth)
        except ValueError:
            depth = 0
        self.entries.append(
            {
                "path": path,
                "title": title,
                "depth": depth,
                "order": len(self.entries),
                "hasChildren": False,
                "virtual": virtual,
            }
        )
        self.seen.add(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_text(encoding="utf-8") == text:
            return
    except FileNotFoundError:
        pass
    path.write_text(text, encoding="utf-8", newline="\n")


def strip_tags(value: str) -> str:
    return html.unescape(TAG_RE.sub(" ", value)).strip()


def parse_title(text: str, fallback: str) -> str:
    match = TITLE_RE.search(text)
    return re.sub(r"\s+", " ", strip_tags(match.group(1))).strip() if match else fallback


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^0-9a-z가-힣_-]+", "-", value.strip().lower()).strip("-_")
    return re.sub(r"-{2,}", "-", slug) or "new-page"


def is_excluded_path(relative_path: str) -> bool:
    return relative_path.replace("\\", "/") in EXCLUDE_FROM_NAV_PATHS


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


def get_nav_entries(dist_root: Path, *, dedupe: bool = False, include_virtual: bool = False) -> list[dict[str, Any]]:
    index_path = dist_root / "guide" / "index.html"
    if not index_path.exists():
        return []
    match = NAV_RE.search(read_text(index_path))
    if not match:
        return []
    parser = NavEntryParser(dist_root, index_path, dedupe)
    parser.feed(match.group(2))
    entries = parser.entries if include_virtual else [entry for entry in parser.entries if not entry.get("virtual")]
    for order, entry in enumerate(entries):
        entry["order"] = order
    for index, entry in enumerate(entries[:-1]):
        entry["hasChildren"] = int(entries[index + 1]["depth"]) > int(entry["depth"])
    annotate_nav_move_flags(entries)
    return entries


def is_movable_nav_entry(entry: dict[str, Any]) -> bool:
    """Return whether a navigation entry can be moved by the editor."""
    path = str(entry.get("path", ""))
    return all(
        [
            bool(path),
            not bool(entry.get("virtual", False)),
            path not in STRUCTURE_MANAGED_PATHS,
            not is_excluded_path(path),
        ]
    )


def subtree_end(entries: list[dict[str, Any]], start_index: int) -> int:
    """Return the exclusive end index for a nav entry and all descendants."""
    start_depth = int(entries[start_index]["depth"])
    end_index = start_index + 1
    while end_index < len(entries) and int(entries[end_index]["depth"]) > start_depth:
        end_index += 1
    return end_index


def previous_sibling_index(entries: list[dict[str, Any]], source_index: int) -> int | None:
    """Return the previous sibling index, or None when the item is first."""
    source_depth = int(entries[source_index]["depth"])
    index = source_index - 1
    while index >= 0:
        depth = int(entries[index]["depth"])
        if depth == source_depth:
            return index
        if depth < source_depth:
            return None
        index -= 1
    return None


def next_sibling_index(entries: list[dict[str, Any]], source_index: int) -> int | None:
    """Return the next sibling index, or None when the item is last."""
    source_depth = int(entries[source_index]["depth"])
    index = subtree_end(entries, source_index)
    if index < len(entries) and int(entries[index]["depth"]) == source_depth:
        return index
    return None


def annotate_nav_move_flags(entries: list[dict[str, Any]]) -> None:
    """Attach same-parent move availability to each nav entry."""
    for index, entry in enumerate(entries):
        entry["canMoveUp"] = is_movable_nav_entry(entry) and previous_sibling_index(entries, index) is not None
        entry["canMoveDown"] = is_movable_nav_entry(entry) and next_sibling_index(entries, index) is not None


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
        is_basic_workflow = str(entry["path"]) == "guide/basic-workflow/index.html"
        if bool(entry.get("virtual", False)):
            anchor = f'<span class="nav-link nav-label" data-depth="{depth}">{title}</span>'
        else:
            href = relative_href(html_path, str(entry["path"]), dist_root)
            anchor = f'<a class="nav-link" href="{href}" data-depth="{depth}">{title}</a>'
        if next_depth > depth:
            open_attr = " open" if depth == 0 else ""
            nav_key = html.escape(str(entry["path"]), quote=True)
            lines.append(f'<details class="nav-group" data-depth="{depth}" data-nav-key="{nav_key}"{open_attr}><summary><span class="nav-caret" aria-hidden="true"></span>{anchor}</summary><div class="nav-children">')
            stack.append(depth)
        elif is_basic_workflow:
            nav_key = html.escape(str(entry["path"]), quote=True)
            lines.append(f'<details class="nav-group nav-single-group nav-basic-workflow-row" data-depth="{depth}" data-nav-key="{nav_key}"><summary><span class="nav-caret nav-caret-static" aria-hidden="true"></span>{anchor}</summary></details>')
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


def _file_item(dist_root: Path, relative_path: str, entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if entry and entry.get("virtual"):
        return {
            "path": relative_path,
            "title": str(entry["title"]),
            "updated": 0,
            "depth": int(entry.get("depth", 0)),
            "inNav": True,
            "movable": False,
            "managed": True,
            "hasChildren": bool(entry.get("hasChildren", False)),
            "virtual": True,
            "canMoveUp": False,
            "canMoveDown": False,
        }
    if is_excluded_path(relative_path):
        return None
    path = dist_root / relative_path
    if not path.exists() or path.name == "404.html":
        return None
    text = read_text(path)
    title = parse_title(text, path.parent.name)
    movable = bool(entry) and relative_path not in STRUCTURE_MANAGED_PATHS and not is_excluded_path(relative_path)
    return {
        "path": relative_path,
        "title": title,
        "updated": int(path.stat().st_mtime),
        "depth": int(entry.get("depth", 0)) if entry else 0,
        "inNav": bool(entry),
        "movable": movable,
        "managed": relative_path in STRUCTURE_MANAGED_PATHS,
        "hasChildren": bool(entry.get("hasChildren", False)) if entry else False,
        "canMoveUp": bool(entry.get("canMoveUp", False)) if entry else False,
        "canMoveDown": bool(entry.get("canMoveDown", False)) if entry else False,
    }


def list_files(dist_root: Path, include_unlisted: bool = True) -> list[dict[str, Any]]:
    entries = get_nav_entries(dist_root, include_virtual=True)
    meta = {entry["path"]: entry for entry in entries}
    unique_entries = sorted(meta.values(), key=lambda entry: int(entry["order"]))
    files: list[dict[str, Any]] = []
    included_paths: set[str] = set()
    for entry in unique_entries:
        entry_path = str(entry["path"])
        item = _file_item(dist_root, entry_path, entry)
        if item:
            files.append(item)
            included_paths.add(entry_path)
    if not include_unlisted:
        return files
    for path in sorted(dist_root.rglob("*.html"), key=lambda p: p.relative_to(dist_root).as_posix()):
        rel = path.relative_to(dist_root).as_posix()
        if rel == "404.html" or rel in included_paths:
            continue
        entry = meta.get(rel)
        item = _file_item(dist_root, rel, entry)
        if item:
            files.append(item)
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
    """Build search index from actual guide HTML files, not only navigation entries.

    Expected failures:
    - Files without article.guide-content are skipped.
    - Non-guide HTML files are skipped.
    """
    items = []
    guide_root = dist_root / "guide"
    for html_path in sorted(guide_root.rglob("*.html"), key=lambda path: path.relative_to(dist_root).as_posix()):
        item_path = html_path.relative_to(dist_root).as_posix()
        if not item_path.startswith("guide/") or html_path.name == "404.html":
            continue
        text = read_text(html_path)
        try:
            article = extract_article(text)
        except ValueError:
            continue
        title = parse_title(text, html_path.parent.name)
        body = re.sub(r"\s+", " ", strip_tags(article))
        guide_url = item_path.removeprefix("guide/")
        items.append({"title": title, "url": guide_url, "path": item_path, "body": body})
    write_text(dist_root / "guide" / "search-index.json", json.dumps(items, ensure_ascii=False, indent=2))


def page_asset_dir(dist_root: Path, html_path: Path) -> Path:
    """Return the asset directory used by newly inserted images for a guide page."""
    relative = html_path.relative_to(dist_root).as_posix()
    parts = relative.split("/")
    page_slug = "index"
    if len(parts) >= 3 and parts[0] == "guide" and parts[-1] == "index.html":
        page_slug = parts[-2]
    elif len(parts) >= 2:
        page_slug = normalize_slug(Path(parts[-1]).stem)
    return dist_root / "guide" / "assets" / page_slug


def next_image_path(asset_dir: Path, extension: str) -> Path:
    """Return image.ext, image 2.ext, ... without overwriting an existing file."""
    used_numbers: set[int] = set()
    pattern = re.compile(r"^image(?: ([2-9][0-9]*))?\.[^.]+$", re.IGNORECASE)
    existing_paths = asset_dir.iterdir() if asset_dir.exists() else []
    for existing_path in existing_paths:
        match = pattern.match(existing_path.name)
        if match:
            used_numbers.add(int(match.group(1) or "1"))
    index = 1
    while index in used_numbers:
        index += 1
    name = "image" if index == 1 else f"image {index}"
    path = asset_dir / f"{name}{extension}"
    while path.exists():
        index += 1
        path = asset_dir / f"image {index}{extension}"
    return path


def save_image(dist_root: Path, html_path: Path, filename: str, mime: str, data_url: str) -> dict[str, Any]:
    if mime not in IMAGE_EXT:
        raise ValueError("PNG/JPG/GIF/WEBP 이미지만 넣을 수 있습니다.")
    prefix = f"data:{mime};base64,"
    if not data_url.startswith(prefix):
        raise ValueError("이미지 데이터가 올바르지 않습니다.")
    assets = page_asset_dir(dist_root, html_path)
    assets.mkdir(parents=True, exist_ok=True)
    path = next_image_path(assets, IMAGE_EXT[mime])
    path.write_bytes(base64.b64decode(data_url[len(prefix):], validate=True))
    return {"ok": True, "path": path.relative_to(dist_root).as_posix(), "src": relative_href(html_path, path.relative_to(dist_root).as_posix(), dist_root)}


def reparent(dist_root: Path, source_path: str, parent_path: str) -> dict[str, Any]:
    source = resolve_html_path(dist_root, source_path).relative_to(dist_root).as_posix()
    if source in STRUCTURE_MANAGED_PATHS or is_excluded_path(source):
        raise ValueError("목차 구조를 관리하는 기본 페이지는 이동할 수 없습니다.")
    entries = get_nav_entries(dist_root, include_virtual=True)
    try:
        parent = resolve_html_path(dist_root, parent_path).relative_to(dist_root).as_posix()
        parent_is_virtual = False
    except FileNotFoundError:
        parent = str(parent_path).replace("\\", "/")
        parent_is_virtual = any(entry["path"] == parent and entry.get("virtual") for entry in entries)
        if not parent_is_virtual:
            raise ValueError("목차에 있는 페이지나 그룹 아래로만 이동할 수 있습니다.")
    if is_excluded_path(parent) and not parent_is_virtual:
        raise ValueError("목차에서 제외된 페이지 아래로 이동할 수 없습니다.")
    source_matches = [i for i, entry in enumerate(entries) if entry["path"] == source]
    parent_matches = [i for i, entry in enumerate(entries) if entry["path"] == parent]
    source_index = source_matches[-1] if source_matches else -1
    parent_index = parent_matches[-1] if parent_matches else -1
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


def reorder_nav_entry(dist_root: Path, source_path: str, direction: str) -> dict[str, Any]:
    """Move a nav entry up or down among siblings without changing its parent.

    Expected failures:
        Raises ValueError when the source is not in the nav, is structure-managed,
        or has no sibling in the requested direction.
    """
    source = resolve_html_path(dist_root, source_path).relative_to(dist_root).as_posix()
    entries = get_nav_entries(dist_root, include_virtual=True)
    source_matches = [index for index, entry in enumerate(entries) if entry["path"] == source]
    source_index = source_matches[-1] if source_matches else -1
    if source_index < 0:
        raise ValueError("목차에 있는 페이지 순서만 바꿀 수 있습니다.")
    if not is_movable_nav_entry(entries[source_index]):
        raise ValueError("목차 구조를 관리하는 기본 페이지는 순서를 바꿀 수 없습니다.")

    clean_direction = direction.strip().lower()
    if clean_direction == "up":
        sibling_index = previous_sibling_index(entries, source_index)
        if sibling_index is None:
            raise ValueError("같은 그룹에서 더 위로 이동할 수 없습니다.")
        source_end = subtree_end(entries, source_index)
        source_block = entries[source_index:source_end]
        previous_block = entries[sibling_index:source_index]
        entries[sibling_index:source_end] = source_block + previous_block
    elif clean_direction == "down":
        source_end = subtree_end(entries, source_index)
        sibling_index = next_sibling_index(entries, source_index)
        if sibling_index is None:
            raise ValueError("같은 그룹에서 더 아래로 이동할 수 없습니다.")
        sibling_end = subtree_end(entries, sibling_index)
        source_block = entries[source_index:source_end]
        next_block = entries[sibling_index:sibling_end]
        entries[source_index:sibling_end] = next_block + source_block
    else:
        raise ValueError("direction은 up 또는 down이어야 합니다.")

    changed = rewrite_navs(dist_root, entries)
    rebuild_search_index(dist_root)
    return {"ok": True, "changed": changed, "path": source, "direction": clean_direction}

EDITOR_HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AIMT Guide Editor</title><style>
:root{color-scheme:light;--bg:#eef2f8;--panel:#fff;--field:#fff;--ink:#182033;--muted:#647084;--line:#d8e0ee;--accent:#315bef;--soft:#edf3ff;--danger:#d92d20;--toolbar:rgba(255,255,255,.94);--shadow:rgba(22,34,56,.08)}@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0f1420;--panel:#151b27;--field:#0f1520;--ink:#e5eaf3;--muted:#98a2b3;--line:#2a3445;--accent:#8ea2ff;--soft:rgba(142,162,255,.16);--danger:#ff8a80;--toolbar:rgba(21,27,39,.94);--shadow:rgba(0,0,0,.32)}}:root[data-theme="dark"]{color-scheme:dark;--bg:#0f1420;--panel:#151b27;--field:#0f1520;--ink:#e5eaf3;--muted:#98a2b3;--line:#2a3445;--accent:#8ea2ff;--soft:rgba(142,162,255,.16);--danger:#ff8a80;--toolbar:rgba(21,27,39,.94);--shadow:rgba(0,0,0,.32)}:root[data-theme="light"]{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.app{display:grid;grid-template-columns:330px minmax(0,1fr);height:100vh}.side{overflow:auto;background:var(--panel);border-right:1px solid var(--line);padding:18px}.main{min-height:0;height:100vh;overflow:auto;padding:18px 22px 22px;display:flex;flex-direction:column}.title{font-size:20px;font-weight:900;margin:0}.hint{font-size:12px;color:var(--muted)}.top{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:0 0 12px}.btn,.theme-select{border:1px solid var(--line);background:var(--field);color:var(--ink);border-radius:10px;padding:8px 10px;cursor:pointer}.btn.primary{border-color:var(--accent);background:var(--accent);color:#fff}.btn:disabled{opacity:.45}.theme-select{margin-left:auto}.filter{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:12px;margin:8px 0 12px;background:var(--field);color:var(--ink)}.file{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;width:100%;text-align:left;border:0;background:transparent;color:var(--ink);border-radius:12px;padding:8px 10px;margin:2px 0;cursor:pointer}.file:hover,.file.active{background:var(--soft)}.file.is-unlisted{opacity:.55}.file[draggable=true]{cursor:grab}.file.dragging{opacity:.45}.file.drop-child{box-shadow:inset 0 0 0 2px var(--accent);background:var(--soft)}.file-main{min-width:0}.file-title{display:block;font-weight:700}.file-path{display:block;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.file-actions{display:flex;gap:3px;align-items:center}.nav-move{width:25px;height:25px;border:1px solid var(--line);border-radius:8px;background:var(--field);color:var(--ink);font-size:13px;line-height:1;cursor:pointer}.nav-move:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}.nav-move:disabled{opacity:.28;cursor:default}.file-tree-marker{display:inline-block;width:1.25em;color:var(--muted)}.file-tree-marker.is-toggle{cursor:pointer;color:var(--accent)}.working-overlay{position:fixed;inset:0;z-index:3000;display:flex;align-items:center;justify-content:center;background:rgba(12,18,32,.42);backdrop-filter:blur(4px)}.working-overlay[hidden]{display:none}.working-box{min-width:240px;max-width:80vw;padding:18px 20px;border:1px solid var(--line);border-radius:16px;background:var(--panel);box-shadow:0 22px 60px rgba(0,0,0,.28);text-align:center}.working-box strong{display:block;margin-bottom:5px}.working-box span{display:block;color:var(--muted);font-size:13px}.editor-card{position:relative;flex:1 1 auto;min-height:0;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:0 18px 40px var(--shadow);overflow:hidden}.toolbar{position:sticky;top:0;z-index:10;display:flex;gap:6px;flex-wrap:wrap;padding:10px;background:var(--toolbar);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.toolbar select{border:1px solid var(--line);border-radius:10px;padding:7px;background:var(--field);color:var(--ink)}.toolbar-menu{position:absolute;z-index:60;min-width:170px;max-width:min(360px,calc(100vw - 48px));max-height:340px;overflow:auto;padding:8px;border:1px solid var(--line);border-radius:12px;background:var(--panel);box-shadow:0 18px 50px var(--shadow)}.toolbar-menu[hidden]{display:none}.callout-menu{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 6px;min-width:290px}.menu-label{grid-column:1/-1;margin:6px 0 2px;color:var(--muted);font-size:11px;font-weight:800}.menu-button{min-width:0;border:1px solid transparent;border-radius:9px;background:transparent;color:var(--ink);padding:7px 8px;text-align:left;cursor:pointer}.menu-button:hover,.menu-button:focus{border-color:var(--accent);background:var(--soft);color:var(--accent);outline:none}.editor-frame{display:block;width:100%;flex:1 1 auto;min-height:360px;height:auto;border:0;background:var(--field)}.source-wrap{flex:0 0 auto;margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 28px var(--shadow);overflow:hidden}.source-wrap>summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;cursor:pointer;color:var(--muted);font-size:13px;font-weight:700}.source-action{padding:6px 9px;font-size:12px;font-weight:700}.source-wrap[open]>summary{border-bottom:1px solid var(--line)}.source-wrap[open]{padding-bottom:12px}.source{display:block;width:calc(100% - 24px);height:48vh;min-height:280px;margin:12px;font-family:Consolas,monospace;font-size:12px;border:1px solid var(--line);border-radius:12px;padding:10px;background:var(--field);color:var(--ink);resize:vertical}.status{font-size:13px;color:var(--muted)}.status.error{color:var(--danger)}@media(max-width:900px){.app{display:block;height:auto}.side{border-right:0;border-bottom:1px solid var(--line)}.main{display:block;height:auto}.editor-card{min-height:72vh}.editor-frame{min-height:64vh}.source{height:54vh}.toolbar{position:sticky;top:0}.theme-select{margin-left:0}}
</style></head><body><div class="working-overlay" id="workingOverlay" hidden><div class="working-box"><strong id="workingTitle">목차를 정리하는 중입니다.</strong><span>잠시만 기다려주세요.</span></div></div><div class="app"><aside class="side"><h1 class="title">AIMT Guide Editor</h1><div class="hint">저장 대상: 현재 저장소 dist HTML<br>새 페이지 기본 위치: 기능별 설명 &gt; 화면 영역</div><div class="top"><button class="btn" id="refreshButton">새로고침</button><button class="btn primary" id="newPageButton">새 페이지</button></div><input class="filter" id="filter" placeholder="목록 검색"><div id="fileList"></div></aside><main class="main"><div class="top"><button class="btn primary" id="saveButton" disabled>저장</button><button class="btn" id="openHtmlButton" disabled>현재 HTML 열기</button><span class="status" id="status">HTML 파일을 불러오는 중입니다.</span><select class="theme-select" id="themeSelect" aria-label="테마 선택"><option value="system">시스템 테마</option><option value="light">밝은 테마</option><option value="dark">어두운 테마</option></select></div><section class="editor-card"><div class="toolbar"><button class="btn" id="formatButton" type="button" aria-haspopup="true" aria-expanded="false">문단</button><div class="toolbar-menu format-menu" id="formatMenu" hidden><button type="button" class="menu-button" data-format="p" data-format-label="문단">문단</button><button type="button" class="menu-button" data-format="h1" data-format-label="제목1">제목1</button><button type="button" class="menu-button" data-format="h2" data-format-label="제목2">제목2</button><button type="button" class="menu-button" data-format="h3" data-format-label="제목3">제목3</button><button type="button" class="menu-button" data-format="pre" data-format-label="코드블록">코드블록</button><button type="button" class="menu-button" data-format="blockquote" data-format-label="인용">인용</button></div><button class="btn" data-cmd="bold">굵게</button><button class="btn" data-cmd="italic">기울임</button><button class="btn" data-cmd="underline">밑줄</button><button class="btn" id="codeButton">코드</button><button class="btn" id="calloutButton" type="button" aria-haspopup="true" aria-expanded="false">콜아웃</button><div class="toolbar-menu callout-menu" id="calloutMenu" hidden><div class="menu-label">파란색</div><button type="button" class="menu-button" data-callout-type="note">note</button><button type="button" class="menu-button" data-callout-type="info">info</button><button type="button" class="menu-button" data-callout-type="todo">todo</button><div class="menu-label">하늘색</div><button type="button" class="menu-button" data-callout-type="abstract">abstract</button><button type="button" class="menu-button" data-callout-type="summary">summary</button><button type="button" class="menu-button" data-callout-type="tldr">tldr</button><button type="button" class="menu-button" data-callout-type="tip">tip</button><button type="button" class="menu-button" data-callout-type="hint">hint</button><button type="button" class="menu-button" data-callout-type="important">important</button><div class="menu-label">녹색</div><button type="button" class="menu-button" data-callout-type="success">success</button><button type="button" class="menu-button" data-callout-type="check">check</button><button type="button" class="menu-button" data-callout-type="done">done</button><div class="menu-label">주황색</div><button type="button" class="menu-button" data-callout-type="question">question</button><button type="button" class="menu-button" data-callout-type="help">help</button><button type="button" class="menu-button" data-callout-type="faq">faq</button><button type="button" class="menu-button" data-callout-type="warning">warning</button><button type="button" class="menu-button" data-callout-type="caution">caution</button><button type="button" class="menu-button" data-callout-type="attention">attention</button><div class="menu-label">빨간색</div><button type="button" class="menu-button" data-callout-type="failure">failure</button><button type="button" class="menu-button" data-callout-type="fail">fail</button><button type="button" class="menu-button" data-callout-type="missing">missing</button><button type="button" class="menu-button" data-callout-type="danger">danger</button><button type="button" class="menu-button" data-callout-type="error">error</button><button type="button" class="menu-button" data-callout-type="bug">bug</button><div class="menu-label">보라색</div><button type="button" class="menu-button" data-callout-type="example">example</button><div class="menu-label">회색</div><button type="button" class="menu-button" data-callout-type="quote">quote</button><button type="button" class="menu-button" data-callout-type="cite">cite</button></div><button class="btn" data-cmd="insertUnorderedList">목록</button><button class="btn" data-cmd="insertOrderedList">번호</button><button class="btn" id="linkButton">링크</button><button class="btn" id="hrButton">구분선</button><button class="btn" id="imageButton">이미지</button><input id="imageInput" type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden></div><iframe class="editor-frame" id="editorFrame" title="guide editor"></iframe></section><details class="source-wrap"><summary><span>HTML 소스보기</span><button class="btn source-action" id="beautifySourceButton" type="button">Beautify</button></summary><textarea class="source" id="sourceBox" spellcheck="false"></textarea></details></main></div><script>
const state={files:[],currentPath:'',draggedPath:'',collapsedPaths:new Set(),collapseReady:false,selectedImage:null};
const fileList=document.getElementById('fileList'),filter=document.getElementById('filter'),statusEl=document.getElementById('status'),frame=document.getElementById('editorFrame'),sourceBox=document.getElementById('sourceBox'),saveButton=document.getElementById('saveButton'),openHtmlButton=document.getElementById('openHtmlButton'),themeSelect=document.getElementById('themeSelect'),beautifySourceButton=document.getElementById('beautifySourceButton'),workingOverlay=document.getElementById('workingOverlay'),workingTitle=document.getElementById('workingTitle');
function showStatus(t,e=false){statusEl.textContent=t;statusEl.className='status'+(e?' error':'')}function showError(e){showStatus(e.message||String(e),true)}async function fetchJson(u,o){const r=await fetch(u,o);const p=await r.json();if(!r.ok)throw new Error(p.error||'요청 실패');return p}function formatTime(ts){return new Date(ts*1000).toLocaleString()}function setWorking(on,title='목차를 정리하는 중입니다.'){workingTitle.textContent=title;workingOverlay.hidden=!on}async function withWorking(title,task){setWorking(true,title);try{return await task()}finally{setWorking(false)}}
const themeKey='aimt-guide-theme';function savedTheme(){try{return localStorage.getItem(themeKey)||'system'}catch(_){return 'system'}}function resolvedTheme(){const t=savedTheme();if(t==='light'||t==='dark')return t;return window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}function applyTheme(){const t=savedTheme();if(t==='light'||t==='dark')document.documentElement.dataset.theme=t;else document.documentElement.removeAttribute('data-theme');if(themeSelect)themeSelect.value=t;const d=frame.contentDocument;if(d&&d.body)d.body.dataset.theme=resolvedTheme()}if(themeSelect){themeSelect.onchange=()=>{try{const v=themeSelect.value;if(v==='light'||v==='dark')localStorage.setItem(themeKey,v);else localStorage.removeItem(themeKey)}catch(_){}applyTheme()}}if(window.matchMedia){const mq=window.matchMedia('(prefers-color-scheme: dark)');if(mq.addEventListener)mq.addEventListener('change',applyTheme)}applyTheme();
async function loadFiles(){const p=await fetchJson('/api/files');state.files=p.files;initializeCollapsedPaths();renderFiles();showStatus('HTML 파일 '+state.files.length+'개를 불러왔습니다.')}function initializeCollapsedPaths(){if(state.collapseReady)return;state.files.forEach(f=>{if(f.hasChildren&&Number(f.depth||0)>=1)state.collapsedPaths.add(f.path)});state.collapseReady=true}
function toggleTreeNode(f,e){e.stopPropagation();if(!f.hasChildren)return;if(state.collapsedPaths.has(f.path))state.collapsedPaths.delete(f.path);else state.collapsedPaths.add(f.path);renderFiles()}function expandAncestors(path){const i=state.files.findIndex(f=>f.path===path);if(i<0)return;let childDepth=Number(state.files[i].depth||0);for(let c=i-1;c>=0;c--){const f=state.files[c],d=Number(f.depth||0);if(d<childDepth){state.collapsedPaths.delete(f.path);childDepth=d}if(childDepth<=0)break}}
function hiddenByCollapse(f,stack){const d=Number(f.depth||0);while(stack.length&&stack[stack.length-1].depth>=d)stack.pop();if(stack.length)return true;if(f.hasChildren&&state.collapsedPaths.has(f.path))stack.push({path:f.path,depth:d});return false}function canDrag(f,searching){return !!(f&&f.inNav&&f.movable&&!searching)}function canOrder(f,searching){return !!(f&&f.inNav&&f.movable&&!searching)}
function renderFiles(){const q=filter.value.trim().toLowerCase();fileList.innerHTML='';const searching=q.length>0,stack=[];const matches=state.files.filter(f=>(f.path+' '+f.title).toLowerCase().includes(q)&&(searching||!hiddenByCollapse(f,stack)));for(const f of matches){const drag=canDrag(f,searching),orderable=canOrder(f,searching),isVirtual=!!f.virtual,b=document.createElement('div');b.role='button';b.tabIndex=0;b.className='file'+(f.path===state.currentPath?' active':'')+(!f.inNav?' is-unlisted':'')+(isVirtual?' is-virtual':'');b.title=f.path+'\n'+(f.updated?formatTime(f.updated):'목차 그룹');b.dataset.path=f.path;b.dataset.inNav=f.inNav?'1':'0';b.dataset.movable=drag?'1':'0';b.draggable=drag;b.style.paddingLeft=(10+Math.min(Number(f.depth||0),6)*16)+'px';b.onclick=e=>{if(e.target.closest('.file-actions'))return;if(isVirtual){toggleTreeNode(f,e);return}loadFile(f.path)};b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();b.click()}};b.addEventListener('dragstart',dragStart);b.addEventListener('dragover',dragOver);b.addEventListener('dragleave',e=>e.currentTarget.classList.remove('drop-child'));b.addEventListener('drop',e=>dropFile(e,f).catch(showError));b.addEventListener('dragend',clearDrop);const main=document.createElement('span');main.className='file-main';const title=document.createElement('span');title.className='file-title';const marker=document.createElement('span');marker.className='file-tree-marker';marker.textContent=f.hasChildren?(state.collapsedPaths.has(f.path)&&!searching?'▸':'▾'):(f.inNav?(drag?'↕':'·'):'·');if(f.hasChildren){marker.classList.add('is-toggle');marker.title=state.collapsedPaths.has(f.path)?'펼치기':'접기';marker.onclick=e=>toggleTreeNode(f,e)}title.append(marker,document.createTextNode(f.title));const p=document.createElement('span');p.className='file-path';p.textContent=f.path;main.append(title,p);const actions=document.createElement('span');actions.className='file-actions';if(f.inNav&&f.movable){[['up','↑','위로 이동',!!f.canMoveUp],['down','↓','아래로 이동',!!f.canMoveDown]].forEach(([dir,label,tip,enabled])=>{const btn=document.createElement('button');btn.type='button';btn.className='nav-move';btn.textContent=label;btn.title=searching?'검색 중에는 순서를 바꿀 수 없습니다.':tip;btn.disabled=!orderable||!enabled;btn.onclick=e=>{e.stopPropagation();moveEntry(f.path,dir).catch(showError)};actions.appendChild(btn)})}b.append(main,actions);fileList.appendChild(b)}if(!matches.length){const empty=document.createElement('div');empty.className='hint';empty.textContent='검색 결과가 없습니다.';fileList.appendChild(empty)}}
function clearDrop(){state.draggedPath='';fileList.querySelectorAll('.dragging,.drop-child').forEach(e=>e.classList.remove('dragging','drop-child'))}function dragStart(e){const b=e.currentTarget;if(b.dataset.movable!=='1'){e.preventDefault();return}state.draggedPath=b.dataset.path;b.classList.add('dragging');e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',state.draggedPath)}function dragOver(e){const b=e.currentTarget;if(!state.draggedPath||b.dataset.inNav!=='1'||b.dataset.path===state.draggedPath)return;e.preventDefault();b.classList.add('drop-child')}async function dropFile(e,target){if(!state.draggedPath||!target||target.path===state.draggedPath){clearDrop();return}e.preventDefault();const source=state.draggedPath;try{await withWorking('목차 위치를 옮기는 중입니다.',async()=>{const p=await fetchJson('/api/reparent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,parent:target.path})});await loadFiles();state.collapsedPaths.delete(target.path);renderFiles();showStatus('하위 페이지로 이동했습니다. 반영 파일: '+p.changed+'개')})}finally{clearDrop()}}async function moveEntry(path,direction){await withWorking('목차 순서를 바꾸는 중입니다.',async()=>{const p=await fetchJson('/api/reorder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:path,direction})});await loadFiles();expandAncestors(path);renderFiles();showStatus((direction==='up'?'위로':'아래로')+' 이동했습니다. 반영 파일: '+p.changed+'개')})}
function doc(){return frame.contentDocument||frame.contentWindow.document}function styles(){return `<style>body{--bg:#fff;--panel:#fff;--ink:#182033;--muted:#647084;--line:#d8e0ee;--accent:#315bef;--soft:#eef3ff;--field:#fff;--code:#101828;--pre-ink:#e5e7eb;--inline-code-bg:#eef2ff;--inline-code-ink:#243b8f;margin:0;padding:28px;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65}body[data-theme="dark"]{--bg:#0f1520;--panel:#151b27;--ink:#e5eaf3;--muted:#98a2b3;--line:#2a3445;--accent:#8ea2ff;--soft:rgba(142,162,255,.16);--field:#0f1520;--code:#090d16;--pre-ink:#e8edf7;--inline-code-bg:#1d2942;--inline-code-ink:#c8d4ff}.guide-content{outline:0;min-height:calc(100vh - 56px);background:var(--panel);color:var(--ink)}.doc-version{font-size:13px;color:var(--muted)}pre{padding:16px;overflow:auto;border-radius:14px;background:var(--code);color:#7ee787}code{padding:.12em .35em;border-radius:6px;background:var(--inline-code-bg);color:var(--inline-code-ink)}pre code{padding:0;border-radius:0;background:transparent;color:inherit}blockquote{padding:12px 16px;border-left:4px solid var(--accent);background:var(--soft);border-radius:12px}table{width:100%;margin:18px 0;border-collapse:collapse;border-spacing:0}th,td{border:1px solid var(--line);padding:8px 10px;vertical-align:top}th{background:var(--soft);font-weight:700}.guide-callout{--callout-color:#2563eb;--callout-bg:#eff6ff;--callout-border:#bfdbfe;--callout-title:#1d4ed8;--callout-text:#1e3a8a;--callout-shadow:rgba(30,58,138,.10);display:block;margin:18px 0;padding:16px 18px;border:1px solid var(--callout-border);border-radius:12px;background:var(--callout-bg);color:var(--callout-text);box-shadow:0 8px 24px var(--callout-shadow)}.guide-callout:before{content:none}.guide-callout-title{margin:0 0 6px;color:var(--callout-title);font-size:16px;font-weight:800;line-height:1.35}.guide-callout-body{min-width:0;color:var(--callout-text);font-size:14px;line-height:1.6}.guide-callout-body>:first-child{margin-top:0}.guide-callout-body>:last-child{margin-bottom:0}.guide-callout[data-callout="abstract"],.guide-callout[data-callout="summary"],.guide-callout[data-callout="tldr"],.guide-callout[data-callout="tip"],.guide-callout[data-callout="hint"],.guide-callout[data-callout="important"]{--callout-color:#0891b2;--callout-bg:#ecfeff;--callout-border:#a5f3fc;--callout-title:#0e7490;--callout-text:#164e63;--callout-shadow:rgba(14,116,144,.10)}.guide-callout[data-callout="success"],.guide-callout[data-callout="check"],.guide-callout[data-callout="done"]{--callout-color:#16a34a;--callout-bg:#f0fdf4;--callout-border:#bbf7d0;--callout-title:#15803d;--callout-text:#14532d;--callout-shadow:rgba(21,128,61,.10)}.guide-callout[data-callout="question"],.guide-callout[data-callout="help"],.guide-callout[data-callout="faq"],.guide-callout[data-callout="warning"],.guide-callout[data-callout="caution"],.guide-callout[data-callout="attention"]{--callout-color:#f59e0b;--callout-bg:#fffbeb;--callout-border:#fcd34d;--callout-title:#b45309;--callout-text:#78350f;--callout-shadow:rgba(120,53,15,.12)}.guide-callout[data-callout="failure"],.guide-callout[data-callout="fail"],.guide-callout[data-callout="missing"],.guide-callout[data-callout="danger"],.guide-callout[data-callout="error"],.guide-callout[data-callout="bug"]{--callout-color:#dc2626;--callout-bg:#fef2f2;--callout-border:#fecaca;--callout-title:#b91c1c;--callout-text:#7f1d1d;--callout-shadow:rgba(127,29,29,.12)}.guide-callout[data-callout="example"]{--callout-color:#7c3aed;--callout-bg:#f5f3ff;--callout-border:#ddd6fe;--callout-title:#6d28d9;--callout-text:#4c1d95;--callout-shadow:rgba(76,29,149,.12)}.guide-callout[data-callout="quote"],.guide-callout[data-callout="cite"]{--callout-color:#64748b;--callout-bg:#f8fafc;--callout-border:#cbd5e1;--callout-title:#475569;--callout-text:#334155;--callout-shadow:rgba(51,65,85,.10)}:root[data-theme="dark"] .guide-callout,body[data-theme="dark"] .guide-callout{--callout-color:#60a5fa;--callout-bg:rgba(37,99,235,.16);--callout-border:rgba(96,165,250,.46);--callout-title:#bfdbfe;--callout-text:#dbeafe;--callout-shadow:rgba(0,0,0,.22)}:root[data-theme="dark"] .guide-callout[data-callout="abstract"],:root[data-theme="dark"] .guide-callout[data-callout="summary"],:root[data-theme="dark"] .guide-callout[data-callout="tldr"],:root[data-theme="dark"] .guide-callout[data-callout="tip"],:root[data-theme="dark"] .guide-callout[data-callout="hint"],:root[data-theme="dark"] .guide-callout[data-callout="important"],body[data-theme="dark"] .guide-callout[data-callout="abstract"],body[data-theme="dark"] .guide-callout[data-callout="summary"],body[data-theme="dark"] .guide-callout[data-callout="tldr"],body[data-theme="dark"] .guide-callout[data-callout="tip"],body[data-theme="dark"] .guide-callout[data-callout="hint"],body[data-theme="dark"] .guide-callout[data-callout="important"]{--callout-color:#22d3ee;--callout-bg:rgba(8,145,178,.16);--callout-border:rgba(103,232,249,.42);--callout-title:#a5f3fc;--callout-text:#cffafe}:root[data-theme="dark"] .guide-callout[data-callout="success"],:root[data-theme="dark"] .guide-callout[data-callout="check"],:root[data-theme="dark"] .guide-callout[data-callout="done"],body[data-theme="dark"] .guide-callout[data-callout="success"],body[data-theme="dark"] .guide-callout[data-callout="check"],body[data-theme="dark"] .guide-callout[data-callout="done"]{--callout-color:#22c55e;--callout-bg:rgba(22,163,74,.16);--callout-border:rgba(134,239,172,.42);--callout-title:#bbf7d0;--callout-text:#dcfce7}:root[data-theme="dark"] .guide-callout[data-callout="question"],:root[data-theme="dark"] .guide-callout[data-callout="help"],:root[data-theme="dark"] .guide-callout[data-callout="faq"],:root[data-theme="dark"] .guide-callout[data-callout="warning"],:root[data-theme="dark"] .guide-callout[data-callout="caution"],:root[data-theme="dark"] .guide-callout[data-callout="attention"],body[data-theme="dark"] .guide-callout[data-callout="question"],body[data-theme="dark"] .guide-callout[data-callout="help"],body[data-theme="dark"] .guide-callout[data-callout="faq"],body[data-theme="dark"] .guide-callout[data-callout="warning"],body[data-theme="dark"] .guide-callout[data-callout="caution"],body[data-theme="dark"] .guide-callout[data-callout="attention"]{--callout-color:#f59e0b;--callout-bg:rgba(245,158,11,.12);--callout-border:rgba(245,158,11,.55);--callout-title:#fbbf24;--callout-text:#fde68a}:root[data-theme="dark"] .guide-callout[data-callout="failure"],:root[data-theme="dark"] .guide-callout[data-callout="fail"],:root[data-theme="dark"] .guide-callout[data-callout="missing"],:root[data-theme="dark"] .guide-callout[data-callout="danger"],:root[data-theme="dark"] .guide-callout[data-callout="error"],:root[data-theme="dark"] .guide-callout[data-callout="bug"],body[data-theme="dark"] .guide-callout[data-callout="failure"],body[data-theme="dark"] .guide-callout[data-callout="fail"],body[data-theme="dark"] .guide-callout[data-callout="missing"],body[data-theme="dark"] .guide-callout[data-callout="danger"],body[data-theme="dark"] .guide-callout[data-callout="error"],body[data-theme="dark"] .guide-callout[data-callout="bug"]{--callout-color:#ef4444;--callout-bg:rgba(220,38,38,.14);--callout-border:rgba(252,165,165,.44);--callout-title:#fca5a5;--callout-text:#fee2e2}:root[data-theme="dark"] .guide-callout[data-callout="example"],body[data-theme="dark"] .guide-callout[data-callout="example"]{--callout-color:#a78bfa;--callout-bg:rgba(124,58,237,.16);--callout-border:rgba(196,181,253,.42);--callout-title:#ddd6fe;--callout-text:#ede9fe}:root[data-theme="dark"] .guide-callout[data-callout="quote"],:root[data-theme="dark"] .guide-callout[data-callout="cite"],body[data-theme="dark"] .guide-callout[data-callout="quote"],body[data-theme="dark"] .guide-callout[data-callout="cite"]{--callout-color:#94a3b8;--callout-bg:rgba(100,116,139,.16);--callout-border:rgba(203,213,225,.36);--callout-title:#e2e8f0;--callout-text:#cbd5e1}@media(prefers-color-scheme:dark){:root:not([data-theme="light"]) .guide-callout{--callout-color:#60a5fa;--callout-bg:rgba(37,99,235,.16);--callout-border:rgba(96,165,250,.46);--callout-title:#bfdbfe;--callout-text:#dbeafe;--callout-shadow:rgba(0,0,0,.22)}:root:not([data-theme="light"]) .guide-callout[data-callout="abstract"],:root:not([data-theme="light"]) .guide-callout[data-callout="summary"],:root:not([data-theme="light"]) .guide-callout[data-callout="tldr"],:root:not([data-theme="light"]) .guide-callout[data-callout="tip"],:root:not([data-theme="light"]) .guide-callout[data-callout="hint"],:root:not([data-theme="light"]) .guide-callout[data-callout="important"]{--callout-color:#22d3ee;--callout-bg:rgba(8,145,178,.16);--callout-border:rgba(103,232,249,.42);--callout-title:#a5f3fc;--callout-text:#cffafe}:root:not([data-theme="light"]) .guide-callout[data-callout="success"],:root:not([data-theme="light"]) .guide-callout[data-callout="check"],:root:not([data-theme="light"]) .guide-callout[data-callout="done"]{--callout-color:#22c55e;--callout-bg:rgba(22,163,74,.16);--callout-border:rgba(134,239,172,.42);--callout-title:#bbf7d0;--callout-text:#dcfce7}:root:not([data-theme="light"]) .guide-callout[data-callout="question"],:root:not([data-theme="light"]) .guide-callout[data-callout="help"],:root:not([data-theme="light"]) .guide-callout[data-callout="faq"],:root:not([data-theme="light"]) .guide-callout[data-callout="warning"],:root:not([data-theme="light"]) .guide-callout[data-callout="caution"],:root:not([data-theme="light"]) .guide-callout[data-callout="attention"]{--callout-color:#f59e0b;--callout-bg:rgba(245,158,11,.12);--callout-border:rgba(245,158,11,.55);--callout-title:#fbbf24;--callout-text:#fde68a}:root:not([data-theme="light"]) .guide-callout[data-callout="failure"],:root:not([data-theme="light"]) .guide-callout[data-callout="fail"],:root:not([data-theme="light"]) .guide-callout[data-callout="missing"],:root:not([data-theme="light"]) .guide-callout[data-callout="danger"],:root:not([data-theme="light"]) .guide-callout[data-callout="error"],:root:not([data-theme="light"]) .guide-callout[data-callout="bug"]{--callout-color:#ef4444;--callout-bg:rgba(220,38,38,.14);--callout-border:rgba(252,165,165,.44);--callout-title:#fca5a5;--callout-text:#fee2e2}:root:not([data-theme="light"]) .guide-callout[data-callout="example"]{--callout-color:#a78bfa;--callout-bg:rgba(124,58,237,.16);--callout-border:rgba(196,181,253,.42);--callout-title:#ddd6fe;--callout-text:#ede9fe}:root:not([data-theme="light"]) .guide-callout[data-callout="quote"],:root:not([data-theme="light"]) .guide-callout[data-callout="cite"]{--callout-color:#94a3b8;--callout-bg:rgba(100,116,139,.16);--callout-border:rgba(203,213,225,.36);--callout-title:#e2e8f0;--callout-text:#cbd5e1}}img{max-width:100%;height:auto;border-radius:12px}.is-selected-image{outline:3px solid var(--accent);outline-offset:3px}.image-tools{position:absolute;z-index:1000;display:flex;gap:4px;padding:6px;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.18)}.image-tools button{border:1px solid var(--line);background:var(--field);color:var(--ink);border-radius:8px;padding:5px 7px}.resize-handle{position:absolute;z-index:999;width:12px;height:12px;background:var(--accent);border:2px solid var(--panel);border-radius:999px}</style>`}
function editorBaseHref(){const p=state.currentPath||'guide/index.html',parts=p.split('/');parts.pop();return '/dist/'+parts.map(encodeURIComponent).join('/')+'/'}function setArticle(a){frame.srcdoc=`<!doctype html><html><head><base href="${editorBaseHref()}">${styles()}</head><body data-theme="${resolvedTheme()}">${a}</body></html>`;sourceBox.value=a;frame.onload=setupFrame}function setupFrame(){applyTheme();const d=doc(),a=d.querySelector('.guide-content');if(!a)return;a.contentEditable='true';a.addEventListener('input',()=>sourceBox.value=getArticle());d.addEventListener('click',e=>{if(e.target&&e.target.tagName==='IMG')selectImage(e.target);else clearImage()});d.addEventListener('paste',e=>{const f=[...(e.clipboardData?.files||[])].find(x=>x.type.startsWith('image/'));if(f){e.preventDefault();insertImage(f).catch(showError)}});a.addEventListener('dragover',e=>{if([...(e.dataTransfer?.files||[])].some(f=>f.type.startsWith('image/')))e.preventDefault()});a.addEventListener('drop',e=>{const f=[...(e.dataTransfer?.files||[])].find(x=>x.type.startsWith('image/'));if(f){e.preventDefault();insertImage(f).catch(showError)}})}
function getArticle(){const d=doc();d.querySelectorAll('.image-tools,.resize-handle').forEach(e=>e.remove());d.querySelectorAll('.is-selected-image').forEach(e=>e.classList.remove('is-selected-image'));return d.querySelector('.guide-content')?.outerHTML||sourceBox.value}const voidTags=new Set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']),rawTags=new Set(['pre','code','textarea','script','style']),blockTags=new Set(['article','section','div','header','footer','main','aside','nav','h1','h2','h3','h4','h5','h6','p','ul','ol','li','table','thead','tbody','tfoot','tr','td','th','blockquote','pre','figure','figcaption','details','summary']);function escapeText(v){return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}function escapeAttr(v){return String(v).replace(/&/g,'&amp;').replace(/"/g,'&quot;')}function openTag(node,tag){const attrs=[...node.attributes].map(a=>' '+a.name+'="'+escapeAttr(a.value)+'"').join('');return '<'+tag+attrs+'>'}function meaningfulNodes(node){return [...node.childNodes].filter(n=>n.nodeType!==3||n.textContent.trim())}function hasBlockChild(nodes){return nodes.some(n=>n.nodeType===1&&blockTags.has(n.tagName.toLowerCase()))}function beautifyNode(node,level){const indent='  '.repeat(level);if(node.nodeType===3){const text=node.textContent.replace(/\s+/g,' ').trim();return text?indent+escapeText(text):''}if(node.nodeType===8)return indent+'<!-- '+node.textContent.trim()+' -->';if(node.nodeType!==1)return '';const tag=node.tagName.toLowerCase();if(rawTags.has(tag))return indent+node.outerHTML.trim();if(voidTags.has(tag))return indent+openTag(node,tag);const nodes=meaningfulNodes(node);if(!nodes.length)return indent+openTag(node,tag)+'</'+tag+'>';if(!hasBlockChild(nodes))return indent+node.outerHTML.trim();const body=nodes.map(n=>beautifyNode(n,level+1)).filter(Boolean).join('\n');return indent+openTag(node,tag)+'\n'+body+'\n'+indent+'</'+tag+'>'}function beautifyHtml(html){const tpl=document.createElement('template');tpl.innerHTML=html.trim();return [...tpl.content.childNodes].map(n=>beautifyNode(n,0)).filter(Boolean).join('\n')}function syncSourceToFrame(){doc().body.innerHTML=sourceBox.value;setupFrame()}function beautifySource(){sourceBox.value=beautifyHtml(sourceBox.value);syncSourceToFrame();showStatus('HTML 소스를 정렬했습니다.')}async function loadFile(path){const p=await fetchJson('/api/file?path='+encodeURIComponent(path));state.currentPath=p.path;setArticle(p.article);saveButton.disabled=false;openHtmlButton.disabled=false;expandAncestors(path);renderFiles();showStatus('열림: '+p.path)}async function saveCurrent(){if(!state.currentPath)return;const article=getArticle();await fetchJson('/api/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:state.currentPath,article})});sourceBox.value=article;showStatus('저장했습니다.');await loadFiles()}
function closeToolbarMenus(){document.querySelectorAll('.toolbar-menu').forEach(m=>m.hidden=true);document.querySelectorAll('#formatButton,#calloutButton').forEach(b=>b.setAttribute('aria-expanded','false'))}function toggleToolbarMenu(button,menu){const shouldOpen=menu.hidden;closeToolbarMenus();if(!shouldOpen)return;menu.hidden=false;const toolbar=button.closest('.toolbar'),maxLeft=Math.max(0,toolbar.clientWidth-menu.offsetWidth-10);menu.style.left=Math.min(button.offsetLeft,maxLeft)+'px';menu.style.top=(button.offsetTop+button.offsetHeight+6)+'px';button.setAttribute('aria-expanded','true')}function applyFormat(value,label){exec('formatBlock',value);document.getElementById('formatButton').textContent=label;closeToolbarMenus()}const calloutTitles={note:'Note',info:'Info',todo:'Todo',abstract:'Abstract',summary:'Summary',tldr:'TLDR',tip:'Tip',hint:'Hint',important:'Important',success:'Success',check:'Check',done:'Done',question:'Question',help:'Help',faq:'FAQ',warning:'Warning',caution:'Caution',attention:'Attention',failure:'Failure',fail:'Fail',missing:'Missing',danger:'Danger',error:'Error',bug:'Bug',example:'Example',quote:'Quote',cite:'Cite'};
const alertCallouts=new Set(['warning','caution','attention','failure','fail','missing','danger','error','bug']);
function insertCallout(type='note'){const d=doc(),w=frame.contentWindow,article=d.querySelector('.guide-content');if(!article){showStatus('본문을 먼저 열어주세요.',true);return}const selection=w.getSelection();let range=null;if(selection&&selection.rangeCount){const candidate=selection.getRangeAt(0);if(article.contains(candidate.commonAncestorContainer))range=candidate}const callout=d.createElement('div'),title=d.createElement('div'),body=d.createElement('div');callout.className='guide-callout';callout.dataset.callout=type;callout.setAttribute('role',alertCallouts.has(type)?'alert':'note');title.className='guide-callout-title';title.textContent=calloutTitles[type]||type;body.className='guide-callout-body';if(range&&!selection.isCollapsed){body.appendChild(range.extractContents())}else{const p=d.createElement('p');p.textContent='내용을 입력하세요.';body.appendChild(p)}callout.append(title,body);if(range)range.insertNode(callout);else article.appendChild(callout);if(selection){selection.removeAllRanges();const nextRange=d.createRange();nextRange.selectNodeContents(body);selection.addRange(nextRange)}sourceBox.value=getArticle();showStatus(type+' 콜아웃을 추가했습니다.');w.focus()}
function exec(cmd,val=null){doc().execCommand(cmd,false,val);sourceBox.value=getArticle();frame.contentWindow.focus()}function wrapSelectionWithCode(){const d=doc(),w=frame.contentWindow,selection=w.getSelection();if(!selection||selection.rangeCount<1||selection.isCollapsed){showStatus('코드로 감쌀 텍스트를 먼저 선택하세요.',true);frame.contentWindow.focus();return}const range=selection.getRangeAt(0);const article=d.querySelector('.guide-content');if(!article||!article.contains(range.commonAncestorContainer)){showStatus('본문 안의 텍스트만 코드로 감쌀 수 있습니다.',true);frame.contentWindow.focus();return}const code=d.createElement('code');code.appendChild(range.extractContents());range.insertNode(code);selection.removeAllRanges();const nextRange=d.createRange();nextRange.selectNodeContents(code);selection.addRange(nextRange);sourceBox.value=getArticle();showStatus('선택 영역에 코드 스타일을 적용했습니다.');frame.contentWindow.focus()}document.querySelectorAll('[data-cmd]').forEach(b=>b.onclick=()=>exec(b.dataset.cmd));document.getElementById('formatButton').onclick=e=>toggleToolbarMenu(e.currentTarget,document.getElementById('formatMenu'));document.querySelectorAll('[data-format]').forEach(b=>b.onclick=e=>applyFormat(e.currentTarget.dataset.format,e.currentTarget.dataset.formatLabel));document.getElementById('codeButton').onclick=wrapSelectionWithCode;document.getElementById('calloutButton').onclick=e=>toggleToolbarMenu(e.currentTarget,document.getElementById('calloutMenu'));document.querySelectorAll('[data-callout-type]').forEach(b=>b.onclick=e=>{closeToolbarMenus();insertCallout(e.currentTarget.dataset.calloutType)});document.addEventListener('click',e=>{if(!e.target.closest('.toolbar-menu')&&!e.target.closest('#formatButton')&&!e.target.closest('#calloutButton'))closeToolbarMenus()});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeToolbarMenus()});document.getElementById('linkButton').onclick=()=>{const u=prompt('링크 주소');if(u)exec('createLink',u)};document.getElementById('hrButton').onclick=()=>exec('insertHorizontalRule');document.getElementById('imageButton').onclick=()=>document.getElementById('imageInput').click();document.getElementById('imageInput').onchange=e=>{const f=e.target.files[0];if(f)insertImage(f).catch(showError);e.target.value=''};
function fileData(f){return new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(f)})}async function insertImage(file){if(!state.currentPath)throw new Error('먼저 문서를 열어주세요.');const dataUrl=await fileData(file);const p=await fetchJson('/api/asset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:state.currentPath,filename:file.name,mime:file.type,dataUrl})});exec('insertHTML',`<p><img src="${p.src}" alt=""></p>`);showStatus('이미지를 넣었습니다: '+p.path)}
function clearImage(){const d=doc();d.querySelectorAll('.image-tools,.resize-handle').forEach(e=>e.remove());d.querySelectorAll('.is-selected-image').forEach(e=>e.classList.remove('is-selected-image'));state.selectedImage=null}function selectImage(img){clearImage();state.selectedImage=img;img.classList.add('is-selected-image');const d=doc(),r=img.getBoundingClientRect(),sx=d.defaultView.scrollX,sy=d.defaultView.scrollY;const tools=d.createElement('div');tools.className='image-tools';tools.style.left=(r.left+sx)+'px';tools.style.top=(r.top+sy-44)+'px';[['왼쪽','left'],['중앙','center'],['오른쪽','right'],['50%','50'],['100%','100']].forEach(([label,val])=>{const b=d.createElement('button');b.textContent=label;b.onclick=()=>imageAction(val);tools.appendChild(b)});d.body.appendChild(tools);const h=d.createElement('span');h.className='resize-handle';h.style.left=(r.right+sx-6)+'px';h.style.top=(r.bottom+sy-6)+'px';h.onmousedown=e=>startResize(e,img);d.body.appendChild(h)}function imageAction(v){const img=state.selectedImage;if(!img)return;if(v==='left'||v==='center'||v==='right'){img.style.display='block';img.style.marginLeft=v==='left'?'0':'auto';img.style.marginRight=v==='right'?'0':'auto'}else{img.style.width=v+'%';img.style.height='auto'}sourceBox.value=getArticle();selectImage(img)}function startResize(e,img){e.preventDefault();const w=doc().defaultView,sx=e.clientX,sy=e.clientY,box=img.getBoundingClientRect(),sw=box.width,sh=box.height,ratio=sw/sh||1;function mv(ev){let nw=Math.max(24,Math.round(sw+ev.clientX-sx)),nh=Math.max(24,Math.round(sh+ev.clientY-sy));if(ev.shiftKey){nh=Math.round(nw/ratio);if(nh<24){nh=24;nw=Math.round(nh*ratio)}}img.style.width=nw+'px';img.style.height=nh+'px'}function up(){w.removeEventListener('mousemove',mv);w.removeEventListener('mouseup',up);sourceBox.value=getArticle();selectImage(img)}w.addEventListener('mousemove',mv);w.addEventListener('mouseup',up)}
sourceBox.addEventListener('input',syncSourceToFrame);beautifySourceButton.onclick=e=>{e.preventDefault();e.stopPropagation();beautifySource()};saveButton.onclick=()=>saveCurrent().catch(showError);document.getElementById('refreshButton').onclick=()=>loadFiles().catch(showError);filter.oninput=renderFiles;openHtmlButton.onclick=()=>{if(state.currentPath)window.open('/dist/'+state.currentPath,'_blank')};document.getElementById('newPageButton').onclick=async()=>{const title=prompt('새 페이지 제목');if(!title)return;const slug=prompt('주소 slug',title.toLowerCase().replace(/\s+/g,'-'))||title;const p=await fetchJson('/api/page',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,slug})});state.collapseReady=false;await loadFiles();await loadFile(p.path)};loadFiles().catch(showError);
</script></body></html>'''

def render_new_page(title: str, relative_path: str, entries: list[dict[str, Any]], dist_root: Path = DIST_ROOT) -> str:
    html_path = dist_root / relative_path
    safe = html.escape(title, quote=False)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe} · AIMT Guide</title><script>(function(){{document.documentElement.dataset.navRestoring="1";try{{var theme=localStorage.getItem("aimt-guide-theme");if(theme==="light"||theme==="dark")document.documentElement.dataset.theme=theme;if(localStorage.getItem("aimt-guide-sidebar-collapsed")==="1")document.documentElement.dataset.sidebar="collapsed";}}catch(_){{}}}})();</script><style id="navRestoreStyle">:root[data-nav-restoring="1"] .nav-list{{visibility:hidden}}:root[data-nav-restoring="1"] .nav-caret{{transition:none}}</style><link rel="stylesheet" href="{relative_href(html_path, 'guide/static/styles.css', dist_root)}"></head><body>  <div id="searchOverlay" class="search-overlay" hidden>    <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="searchTitle">      <div class="search-header"><h2 id="searchTitle">문서 검색</h2><button id="searchClose" class="search-close" type="button" aria-label="검색 닫기" title="검색 닫기">×</button></div>      <input id="guideSearch" class="search-input" type="search" placeholder="검색어 입력" autocomplete="off">      <div id="searchResults" class="search-results" hidden></div>    </section>  </div><button id="sidebarExpand" class="sidebar-expand sidebar-toggle" type="button" aria-label="사이드바 열기" title="사이드바 열기">☰</button><div class="site-shell"><aside class="sidebar"><div class="brand-row"><a class="brand" href="{relative_href(html_path, 'guide/index.html', dist_root)}">AIMT GUIDE</a><button id="searchOpen" class="sidebar-toggle" type="button" aria-label="문서 검색" title="문서 검색">⌕</button><button id="themeToggle" class="theme-toggle" type="button" aria-label="테마 변경" title="테마 변경">◐</button><button id="sidebarCollapse" class="sidebar-toggle" type="button" aria-label="사이드바 닫기" title="사이드바 닫기">←</button></div><nav class="nav-list" aria-label="문서 목록">
{build_nav(entries, html_path, dist_root)}
      </nav></aside><div id="sidebarResizer" class="sidebar-resizer" role="separator" aria-label="사이드바 너비 조절" aria-orientation="vertical" tabindex="0"></div><main class="content-shell"><article class="guide-content"><h1>{safe}</h1><p class="doc-version">{DOC_VERSION}<br>최종 편집 일시: 편집기 생성</p><h2>무엇을 할 수 있나요?</h2><p>새 문서입니다. 사용자가 이 문서에서 무엇을 판단하거나 실행할 수 있는지 작성해주세요.</p><h2>완료 후 확인</h2><ul><li>설명대로 진행했을 때 사용자가 다음 행동을 알 수 있는지 확인합니다.</li></ul></article></main></div><script src="{relative_href(html_path, 'guide/static/main.js', dist_root)}"></script></body></html>'''


def insert_after_subtree(entries: list[dict[str, Any]], parent_path: str, entry: dict[str, Any]) -> None:
    parent_matches = [index for index, item in enumerate(entries) if item["path"] == parent_path]
    parent_index = parent_matches[-1] if parent_matches else -1
    if parent_index < 0:
        entries.insert(1 if entries else 0, entry)
        return
    parent_depth = int(entries[parent_index]["depth"])
    insert_index = parent_index + 1
    while insert_index < len(entries) and int(entries[insert_index]["depth"]) > parent_depth:
        insert_index += 1
    entry["depth"] = parent_depth + 1
    entries.insert(insert_index, entry)


def create_page(dist_root: Path, title: str, slug: str, parent_path: str = "") -> dict[str, Any]:
    clean_title = title.strip() or "새 문서"
    clean_slug = normalize_slug(slug or clean_title)
    relative = f"guide/{clean_slug}/index.html"
    path = dist_root / relative
    if path.exists():
        raise ValueError("이미 같은 주소의 문서가 있습니다.")
    entries = get_nav_entries(dist_root)
    parent = parent_path.strip() or DEFAULT_NEW_PAGE_PARENT
    if parent and not any(entry["path"] == parent for entry in entries):
        parent = DEFAULT_NEW_PAGE_PARENT if any(entry["path"] == DEFAULT_NEW_PAGE_PARENT for entry in entries) else ""
    new_entry = {"path": relative, "title": clean_title, "depth": 1, "order": 0, "hasChildren": False}
    insert_after_subtree(entries, parent, new_entry)
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
                    self.send_payload(self.get_files(parsed.query))
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
                    self.send_payload(json_response(create_page(DIST_ROOT, str(payload.get("title", "")), str(payload.get("slug", "")), str(payload.get("parent", "")))))
                case "/api/reparent":
                    self.send_payload(json_response(reparent(DIST_ROOT, str(payload.get("source", "")), str(payload.get("parent", "")))))
                case "/api/reorder":
                    self.send_payload(json_response(reorder_nav_entry(DIST_ROOT, str(payload.get("source", "")), str(payload.get("direction", "")))))
                case _:
                    self.send_payload(json_response({"error": "지원하지 않는 경로입니다."}, 404))
        except Exception as exc:
            self.send_payload(json_response({"error": str(exc)}, 400))

    def get_file(self, query: str) -> tuple[int, bytes, str]:
        path = resolve_html_path(DIST_ROOT, parse_qs(query).get("path", [""])[0])
        text = read_text(path)
        return json_response({"path": path.relative_to(DIST_ROOT).as_posix(), "title": parse_title(text, path.stem), "article": extract_article(text)})

    def get_files(self, query: str) -> tuple[int, bytes, str]:
        params = parse_qs(query)
        include_unlisted = params.get("includeUnlisted", ["0"])[0].lower() in {"1", "true", "yes"}
        return json_response({"files": list_files(DIST_ROOT, include_unlisted=include_unlisted)})

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
        raise SystemExit("dist가 없습니다. 먼저 dist를 복원하거나 가이드를 재생성해주세요.")
    server = ThreadingHTTPServer((HOST, PORT), GuideEditorHandler)
    print(f"AIMT Guide Editor: http://{HOST}:{PORT}/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
