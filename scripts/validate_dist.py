from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

def find_site_root() -> Path:
    current = Path(__file__).resolve().parents[1]
    if (current / "dist").exists() or (current / "ExportBlock").exists():
        return current
    return Path(__file__).resolve().parents[3] / "docs" / "guide-site"


SITE_ROOT = find_site_root()
DIST_ROOT = SITE_ROOT / "dist"
HTML_RE = re.compile(r"(?is)<(?:a|link)\b[^>]+href=[\"']([^\"']+)[\"']|<(?:img|script)\b[^>]+src=[\"']([^\"']+)[\"']")
LOCAL_PATH_RE = re.compile(
    rf"{re.escape(str(SITE_ROOT))}|file:///{re.escape(str(SITE_ROOT).replace('\\', '/'))}",
    re.IGNORECASE,
)


def iter_html_files(dist_root: Path) -> list[Path]:
    return sorted(dist_root.rglob("*.html"))


def is_external_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "mailto", "tel", "data", "javascript"}


def resolve_internal_target(html_path: Path, raw_url: str) -> Path | None:
    url, _fragment = urldefrag(raw_url.strip())
    if not url or is_external_url(url):
        return None
    if url.startswith("/AIMT_Build/"):
        relative = url.removeprefix("/AIMT_Build/")
        return (DIST_ROOT / unquote(relative)).resolve()
    if url.startswith("/dist/"):
        return (DIST_ROOT / unquote(url.removeprefix("/dist/"))).resolve()
    if url.startswith("/"):
        return (DIST_ROOT / unquote(url.lstrip("/"))).resolve()
    return (html_path.parent / unquote(url)).resolve()


def validate_dist(dist_root: Path = DIST_ROOT) -> list[str]:
    errors: list[str] = []
    required = [
        dist_root / "index.html",
        dist_root / ".nojekyll",
        dist_root / "guide" / "index.html",
        dist_root / "guide" / "search-index.json",
        dist_root / "404.html",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"required file missing: {path}")
    for html_path in iter_html_files(dist_root):
        text = html_path.read_text(encoding="utf-8", errors="replace")
        if LOCAL_PATH_RE.search(text):
            errors.append(f"local workspace path leaked: {html_path}")
        for match in HTML_RE.finditer(text):
            raw_url = match.group(1) or match.group(2) or ""
            target = resolve_internal_target(html_path, raw_url)
            if target is not None and raw_url.lower().split("#", 1)[0].endswith(".md"):
                errors.append(f"markdown link remains: {html_path} -> {raw_url}")
            if target is None:
                continue
            try:
                target.relative_to(dist_root.resolve())
            except ValueError:
                errors.append(f"internal target escapes dist: {html_path} -> {raw_url}")
                continue
            if raw_url.endswith("/") or target.suffix == "":
                target = target / "index.html"
            if not target.exists():
                errors.append(f"missing internal target: {html_path} -> {raw_url}")
    return errors


def main() -> int:
    errors = validate_dist()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Dist validation complete: html={len(iter_html_files(DIST_ROOT))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
