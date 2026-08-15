from __future__ import annotations

import argparse
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_health(port: int, process: subprocess.Popen[str], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    address = f"http://127.0.0.1:{port}/health"
    last_error = "service did not respond"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.communicate()[0].strip()
            raise RuntimeError(
                f"VenueView exited before becoming healthy. {output or last_error}"
            )
        try:
            with urllib.request.urlopen(address, timeout=1) as response:
                if response.status == 200 and response.read() == b'{"status":"ok"}\n':
                    return
                last_error = f"unexpected health response: {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"VenueView health check timed out: {last_error}")


def verify_rules_source(port: int, expected: str) -> None:
    address = f"http://127.0.0.1:{port}/"
    with urllib.request.urlopen(address, timeout=3) as response:
        body = response.read().decode("utf-8")
    marker = f'data-rules-source="{expected}"'
    if expected == "none":
        if "data-rules-source=" in body:
            raise RuntimeError("Public VenueView bundle unexpectedly loaded private rules.")
        return
    if marker not in body:
        raise RuntimeError(
            f"VenueView bundle did not activate the expected {expected!r} rule source."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a VenueView desktop bundle")
    parser.add_argument("executable", type=Path)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument(
        "--expect-rules-source",
        choices=("none", "bundled"),
        default="none",
    )
    args = parser.parse_args(argv)
    executable = args.executable.resolve()
    if not executable.is_file():
        parser.error(f"Desktop executable not found: {executable}")

    with tempfile.TemporaryDirectory(prefix="venueview-smoke-") as temporary:
        environment = os.environ.copy()
        environment["VENUEVIEW_PRIVATE_RULES_PATH"] = str(
            Path(temporary) / "private_rules.json"
        )
        port = available_port()
        process = subprocess.Popen(
            [str(executable), "--no-browser", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=environment,
        )
        try:
            wait_for_health(port, process, args.timeout)
            verify_rules_source(port, args.expect_rules_source)
            print(
                "VenueView desktop health and rule-source checks passed on "
                f"127.0.0.1:{port}"
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
