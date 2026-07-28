"""Archipelago Launcher entry point for the external DOOM integration files."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import sys
import traceback
from pathlib import Path

import settings
from Utils import messagebox

BRIDGE_PROTOCOL = 3


def _client_directory() -> Path:
    configured = settings.get_settings()["doometernal_options"][
        "client_directory"
    ]
    configured_path = Path(
        os.path.expandvars(os.path.expanduser(str(configured)))
    )
    candidates = [
        configured_path,
        configured_path / "client",
    ]

    # Never fall back to a global/download/repository copy: the configured
    # extracted release is the only authority for the bridge being launched.
    for path in candidates:
        if (path / "bridge_client.py").is_file():
            return path

    return configured_path


def _bridge_identity(bridge: Path) -> tuple[str, str]:
    """Validate packaged bridge identity without importing its code."""
    identity_path = bridge.with_name("bridge_identity.json")
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "Missing or invalid bridge_identity.json beside bridge_client.py. "
            "Re-extract matching DOOM Eternal Archipelago release client."
        ) from error

    actual_sha = hashlib.sha256(bridge.read_bytes()).hexdigest()
    expected_revision = f"mission-unified-{actual_sha[:12]}"
    if identity.get("protocol") != BRIDGE_PROTOCOL:
        raise RuntimeError(
            f"Bridge protocol {identity.get('protocol')!r} is incompatible with "
            f"APWorld protocol {BRIDGE_PROTOCOL}. Re-extract matching release."
        )
    if identity.get("sha256") != actual_sha or identity.get("revision") != expected_revision:
        raise RuntimeError(
            "Bridge SHA/revision does not match bridge_identity.json. "
            "Re-extract matching DOOM Eternal Archipelago release client."
        )
    return actual_sha, expected_revision


def launch(*launch_args: str) -> None:
    client_directory = _client_directory()
    bridge = client_directory / "bridge_client.py"
    if not bridge.is_file():
        messagebox(
            "DOOM Eternal Client files not found",
            f"Searched in: {client_directory}\n\n"
            "Open Archipelago Settings and set "
            "doom_eternal_options.client_directory to the Mod folder "
            "where 'bridge_client.py' and 'ap_client.exe' are located.",
            error=True,
        )
        return

    try:
        bridge_sha256, bridge_revision = _bridge_identity(bridge)
    except RuntimeError as error:
        messagebox("DOOM Eternal bridge mismatch", str(error), error=True)
        return

    print(f"BRIDGE_REVISION={bridge_revision}")
    print(f"BRIDGE_FILE={bridge.resolve()}")
    print(f"BRIDGE_SHA256={bridge_sha256}")
    print(f"BRIDGE_PROTOCOL={BRIDGE_PROTOCOL}")

    os.chdir(client_directory)
    sys.path.insert(0, str(client_directory))
    try:
        bridge_globals = runpy.run_path(
            str(bridge), run_name="doom_eternal_external_client"
        )
        bridge_globals["launch"](*launch_args)
    except Exception as error:
        traceback.print_exc()
        messagebox(
            "DOOM Eternal Client failed to start",
            f"{type(error).__name__}: {error}\n\n"
            "Rebuild and re-extract the matching playable client. "
            "The traceback was also written to the Launcher output.",
            error=True,
        )
