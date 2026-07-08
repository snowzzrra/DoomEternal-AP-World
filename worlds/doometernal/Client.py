"""Archipelago Launcher entry point for the external DOOM integration files."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import settings
from Utils import messagebox


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
        Path.home() / "DoomEternalArchipelago",
        Path.home() / "DoomEternalArchipelago" / "client",
        Path.home() / "Downloads" / "DoomEternalArchipelagoPlayableTest",
        Path.home() / "Downloads" / "DoomEternalArchipelagoPlayableTest" / "client",
    ]
    
    # Try finding bridge_client.py in any candidate directory
    for path in candidates:
        if (path / "bridge_client.py").is_file():
            return path
            
    # If not found, search one level deep in the configured path
    if configured_path.is_dir():
        for subpath in configured_path.iterdir():
            if subpath.is_dir() and (subpath / "bridge_client.py").is_file():
                return subpath

    return configured_path


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

    os.chdir(client_directory)
    sys.path.insert(0, str(client_directory))
    bridge_globals = runpy.run_path(
        str(bridge), run_name="doom_eternal_external_client"
    )
    bridge_globals["launch"](*launch_args)
