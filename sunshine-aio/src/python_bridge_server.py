"""Minimal Python backend bridge for the Sunshine AIO Electron frontend.

Reads newline-delimited JSON commands from stdin and writes newline-delimited
JSON responses to stdout. The protocol is intentionally tiny for Story 1.3 so
the integration can be validated end-to-end before richer commands are added.

Each request line is expected to look like:

    {"id": "<opaque-string>", "cmd": "<command-name>", "params": {...}}

Each response line is one of:

    {"id": "<opaque-string>", "ok": true, "result": <any-json-value>}
    {"id": "<opaque-string>", "ok": false, "error": "<human-readable message>"}

Closing stdin (EOF) terminates the loop and the process exits cleanly.

The module is also runnable as a script for manual smoke testing:

    python python_bridge_server.py
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict


def _build_pong(params: Any) -> Dict[str, Any]:
    """Return the pong payload. Intentionally does NOT echo params: the
    ping command is parameterless by contract, and the round-trip
    identity is verified by matching the request id (the bridge matches
    responses to requests by id, not by payload). Echoing params was
    useful as a smoke-test scaffold but would leak arbitrary renderer
    arguments into log lines and the future electronAPI surface if a
    caller ever passed sensitive data through the no-op params slot.
    The payload shape is therefore fixed to ``{"result": "pong"}``."""
    return {"result": "pong"}


# Command dispatch table. Adding a new command means adding an entry here
# AND keeping it backwards compatible — the Electron side has a typed bridge.
COMMANDS = {
    "ping": _build_pong,
}


def _emit(response: Dict[str, Any]) -> None:
    """Write one response line and flush immediately. Flushing matters:
    the Electron side parses stdout line-by-line; if we buffer stdout the
    parent would sit waiting forever for a response that has already been
    computed."""
    sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _handle_line(raw_line: str) -> bool:
    """Process one stdin line. Returns False to request loop exit."""
    line = raw_line.strip()
    if not line:
        # Ignore empty keep-alive lines silently rather than erroring.
        return True

    request_id: Any = None
    try:
        request = json.loads(line)
    except json.JSONDecodeError as exc:
        # We cannot include the id because we never parsed the envelope.
        _emit({"ok": False, "error": f"invalid JSON: {exc.msg}"})
        return True

    if not isinstance(request, dict):
        _emit({"ok": False, "error": "request must be a JSON object"})
        return True

    request_id = request.get("id")
    cmd = request.get("cmd")
    params = request.get("params", {})

    if not isinstance(cmd, str) or not cmd:
        _emit({"id": request_id, "ok": False, "error": "missing or invalid 'cmd'"})
        return True

    handler = COMMANDS.get(cmd)
    if handler is None:
        _emit({
            "id": request_id,
            "ok": False,
            "error": f"unknown command: {cmd}",
        })
        return True

    try:
        result = handler(params)
    except Exception as exc:  # noqa: BLE001 — last-resort guard
        # Surface a clean error envelope rather than a Python traceback.
        # We deliberately do NOT include the traceback in the response:
        # tracebacks can leak install paths, library versions, file names,
        # and other environment details that are useful to an attacker
        # if any future story forwards these errors to telemetry. The
        # full traceback is logged to stderr (server-side) for diagnosis.
        safe_error = f"{type(exc).__name__}: {exc}"
        # Log full traceback to stderr only — never to the renderer.
        print(
            f"[python_bridge_server] handler '{cmd}' raised: {safe_error}\n{traceback.format_exc(limit=5)}",
            file=sys.stderr,
            flush=True,
        )
        _emit({
            "id": request_id,
            "ok": False,
            "error": safe_error,
        })
        return True

    _emit({"id": request_id, "ok": True, "result": result})
    return True


def main() -> int:
    """Main loop. Returns the process exit code."""
    _emit({"ok": True, "event": "ready", "pid": __import__("os").getpid()})
    try:
        for raw_line in sys.stdin:
            if not _handle_line(raw_line):
                break
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C / parent signal. We do not raise
        # because that would dump a traceback into stderr and obscure
        # the clean shutdown path.
        return 0
    except BrokenPipeError:
        # The parent (Electron) closed our stdin; this is a normal exit
        # during app shutdown, not an error to report.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
