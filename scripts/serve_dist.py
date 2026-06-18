from __future__ import annotations

import argparse
import functools
import socket
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import NoReturn


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_START_PATH = "/guide/"


class QuietStaticHandler(SimpleHTTPRequestHandler):
    """Static file handler with concise request logs."""

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")


def find_repo_root() -> Path:
    """Return the repository root based on this script location."""

    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Expected failures:
        argparse exits when an unsupported option or invalid value is provided.
    """

    parser = argparse.ArgumentParser(description="Serve the generated AIMT guide from dist.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind host. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Start port. Default: {DEFAULT_PORT}")
    parser.add_argument("--root", type=Path, default=find_repo_root() / "dist", help="Static root. Default: ./dist")
    parser.add_argument("--path", default=DEFAULT_START_PATH, help=f"Browser path. Default: {DEFAULT_START_PATH}")
    parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser.")
    parser.add_argument("--strict-port", action="store_true", help="Fail instead of trying the next port.")
    return parser.parse_args()


def validate_root(root: Path) -> Path:
    """Resolve and validate the static root.

    Raises:
        FileNotFoundError: when the root does not exist.
        NotADirectoryError: when the root is not a directory.
    """

    resolved = root.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"static root not found: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"static root is not a directory: {resolved}")
    return resolved


def is_port_available(host: str, port: int) -> bool:
    """Return whether the host and port can be bound."""

    try:
        with socket.create_server((host, port), reuse_port=False):
            return True
    except OSError:
        return False


def pick_port(host: str, start_port: int, strict_port: bool) -> int:
    """Pick an available port.

    Raises:
        OSError: when strict_port is enabled and the requested port is unavailable.
        RuntimeError: when no available port is found in the scan range.
    """

    if strict_port:
        if is_port_available(host, start_port):
            return start_port
        raise OSError(f"port is already in use: {host}:{start_port}")

    for port in range(start_port, start_port + 100):
        if is_port_available(host, port):
            return port
    raise RuntimeError(f"no available port found from {start_port} to {start_port + 99}")


def normalize_browser_path(path: str) -> str:
    """Return a browser path that starts with '/'."""

    return path if path.startswith("/") else f"/{path}"


def build_url(host: str, port: int, path: str) -> str:
    """Build the local URL shown to the user and opened in the browser."""

    return f"http://{host}:{port}{normalize_browser_path(path)}"


def serve_forever(root: Path, host: str, port: int, url: str) -> NoReturn:
    """Start the static server and block until interrupted."""

    handler = functools.partial(QuietStaticHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"AIMT guide server: {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        raise SystemExit(0)
    finally:
        server.server_close()


def main() -> int:
    """CLI entry point."""

    args = parse_args()
    try:
        root = validate_root(args.root)
        port = pick_port(args.host, args.port, args.strict_port)
    except (FileNotFoundError, NotADirectoryError, OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    url = build_url(args.host, port, args.path)
    if not args.no_browser:
        webbrowser.open(url)
    serve_forever(root=root, host=args.host, port=port, url=url)


if __name__ == "__main__":
    raise SystemExit(main())
