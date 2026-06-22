from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import edit_guide
import validate_dist


ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = edit_guide.DIST_ROOT
GUIDE_ROOT = DIST_ROOT / "guide"
FORBIDDEN_PATTERNS = (
    "AIMT_Build",
    ".codex",
)


def _print(message: str) -> None:
    print(message)


def _run_python(args: Sequence[str]) -> int:
    command = [sys.executable, *args]
    return subprocess.call(command, cwd=ROOT)


def _guide_html_files() -> list[Path]:
    return sorted(GUIDE_ROOT.rglob("index.html"))


def _load_search_index() -> list[dict[str, Any]]:
    path = GUIDE_ROOT / "search-index.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _entry_signature(entry: dict[str, Any]) -> tuple[str, str, int, bool]:
    return (
        str(entry.get("path", "")),
        str(entry.get("title", "")),
        int(entry.get("depth", 0)),
        bool(entry.get("virtual", False)),
    )


def _current_nav_entries() -> list[dict[str, Any]]:
    return edit_guide.get_nav_entries(DIST_ROOT, include_virtual=True)


def _canonical_nav_entries() -> list[dict[str, Any]]:
    import renew_user_manual

    return renew_user_manual._make_nav(_current_nav_entries())


def _select_nav_entries(canonical: bool) -> list[dict[str, Any]]:
    return _canonical_nav_entries() if canonical else _current_nav_entries()


def _compile_scripts(paths: Sequence[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path}: {exc.msg}")
    return errors


def _iter_text_targets() -> list[Path]:
    suffixes = {".html", ".json", ".js", ".css"}
    return sorted(path for path in DIST_ROOT.rglob("*") if path.suffix.lower() in suffixes)


def command_status(_args: argparse.Namespace) -> int:
    entries = _current_nav_entries()
    listed_paths = {entry["path"] for entry in entries if not entry.get("virtual")}
    html_paths = {path.relative_to(DIST_ROOT).as_posix() for path in _guide_html_files()}
    search_items = _load_search_index()
    _print(f"dist: {DIST_ROOT}")
    _print(f"guide pages: {len(html_paths)}")
    _print(f"nav entries: {len(entries)}")
    _print(f"nav listed pages: {len(listed_paths)}")
    _print(f"unlisted guide pages: {len(html_paths - listed_paths)}")
    _print(f"search index items: {len(search_items)}")
    return 0


def command_search(_args: argparse.Namespace) -> int:
    edit_guide.rebuild_search_index(DIST_ROOT)
    _print("Search index rebuilt from current dist guide articles.")
    return 0


def command_nav(args: argparse.Namespace) -> int:
    entries = _select_nav_entries(args.canonical)
    changed = edit_guide.rewrite_navs(DIST_ROOT, entries)
    if args.search:
        edit_guide.rebuild_search_index(DIST_ROOT)
    mode = "canonical" if args.canonical else "current"
    _print(f"Navigation rewritten from {mode} entries: html={changed}")
    return 0


def command_sync(args: argparse.Namespace) -> int:
    nav_args = argparse.Namespace(canonical=args.canonical, search=True)
    exit_code = command_nav(nav_args)
    if exit_code:
        return exit_code
    return command_validate(argparse.Namespace(compile=args.compile, leaks=args.leaks))


def command_renew(args: argparse.Namespace) -> int:
    if not args.yes:
        _print("Refusing to renew articles without --yes. This command rewrites guide article bodies.")
        return 2
    return _run_python(["scripts/renew_user_manual.py"])


def command_validate(args: argparse.Namespace) -> int:
    if args.compile:
        errors = _compile_scripts(sorted((ROOT / "scripts").glob("*.py")))
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        _print("Python compile check passed.")
    errors = validate_dist.validate_dist(DIST_ROOT)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    _print(f"Dist validation passed: html={len(validate_dist.iter_html_files(DIST_ROOT))}")
    return command_leaks(args) if args.leaks else 0


def command_leaks(_args: argparse.Namespace) -> int:
    hits: list[str] = []
    for path in _iter_text_targets():
        text = path.read_text(encoding="utf-8", errors="replace")
        hits.extend(f"{path}: {pattern}" for pattern in FORBIDDEN_PATTERNS if pattern in text)
    if hits:
        print("\n".join(hits), file=sys.stderr)
        return 1
    _print("Forbidden guide exposure check passed.")
    return 0


def command_compare_nav(_args: argparse.Namespace) -> int:
    current = [_entry_signature(entry) for entry in _current_nav_entries()]
    canonical = [_entry_signature(entry) for entry in _canonical_nav_entries()]
    if current == canonical:
        _print(f"Navigation matches canonical script output: entries={len(current)}")
        return 0
    _print(f"Navigation differs: current={len(current)}, canonical={len(canonical)}")
    return 1


def command_serve(args: argparse.Namespace) -> int:
    command = ["scripts/serve_dist.py", "--host", args.host, "--port", str(args.port), "--path", args.path]
    if args.no_browser:
        command.append("--no-browser")
    if args.strict_port:
        command.append("--strict-port")
    return _run_python(command)


def command_editor(_args: argparse.Namespace) -> int:
    return _run_python(["scripts/edit_guide.py"])


def _add_bool_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--canonical", action="store_true", help="renew_user_manual.py의 목차 규칙으로 재구성합니다.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIMT guide maintenance CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _register_commands(subparsers)
    return parser


def _register_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    _set(subparsers.add_parser("status", help="현재 dist/guide 상태를 요약합니다."), command_status)
    _set(subparsers.add_parser("search", help="현재 HTML 본문 기준으로 search-index.json만 재생성합니다."), command_search)
    nav = subparsers.add_parser("nav", help="목차만 모든 HTML에 다시 씁니다.")
    _add_bool_flags(nav)
    nav.add_argument("--no-search", dest="search", action="store_false", help="목차 재작성 후 검색 인덱스를 갱신하지 않습니다.")
    nav.set_defaults(search=True, func=command_nav)
    sync = subparsers.add_parser("sync", help="목차와 검색 인덱스를 갱신한 뒤 검증합니다.")
    _add_bool_flags(sync)
    sync.add_argument("--no-compile", dest="compile", action="store_false", help="Python compile 검사를 생략합니다.")
    sync.add_argument("--leaks", action="store_true", help="금지 문자열 노출도 함께 검사합니다.")
    sync.set_defaults(compile=True, func=command_sync)
    renew = subparsers.add_parser("renew", help="본문까지 공식 템플릿 기준으로 전면 재작성합니다.")
    renew.add_argument("--yes", action="store_true", help="본문 재작성 위험을 확인하고 실행합니다.")
    renew.set_defaults(func=command_renew)
    validate = subparsers.add_parser("validate", help="dist 정적 검증을 실행합니다.")
    validate.add_argument("--compile", action="store_true", help="scripts/*.py compile 검사를 함께 실행합니다.")
    validate.add_argument("--leaks", action="store_true", help="금지 문자열 노출도 함께 검사합니다.")
    validate.set_defaults(func=command_validate)
    _set(subparsers.add_parser("leaks", help="dist 안의 금지 문자열 노출을 검사합니다."), command_leaks)
    _set(subparsers.add_parser("compare-nav", help="현재 목차와 생성 스크립트 목차가 같은지 비교합니다."), command_compare_nav)
    serve = subparsers.add_parser("serve", help="로컬 가이드 서버를 실행합니다.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--path", default="/guide/")
    serve.add_argument("--no-browser", action="store_true")
    serve.add_argument("--strict-port", action="store_true")
    serve.set_defaults(func=command_serve)
    _set(subparsers.add_parser("editor", help="가이드 에디터 서버를 실행합니다."), command_editor)


def _set(parser: argparse.ArgumentParser, func: Callable[[argparse.Namespace], int]) -> None:
    parser.set_defaults(func=func)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
