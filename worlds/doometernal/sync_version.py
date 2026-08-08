"""Synchronize official APWorld identity into mod-owned release metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

WORLD_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = WORLD_DIR / "archipelago.json"
WORLD_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _load_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest.get("world_version")
    if not isinstance(manifest.get("game"), str):
        raise ValueError("archipelago.json requires string game")
    if not isinstance(version, str) or not WORLD_VERSION_PATTERN.fullmatch(version):
        raise ValueError("archipelago.json world_version must use major.minor.build")
    forbidden = {"release_label", "version", "compatible_version"} & manifest.keys()
    if forbidden:
        raise ValueError(f"unsupported archipelago.json fields: {', '.join(sorted(forbidden))}")
    return manifest


def _write(path: Path, payload: str, check: bool) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == payload:
        return
    if check:
        raise ValueError(f"stale version projection: {path}")
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    temporary.replace(path)


def sync(*, check: bool, mod_root: Path | None = None) -> None:
    manifest = _load_manifest()
    if mod_root is None:
        return
    identity_path = mod_root / "data" / "content_identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity["game"] = manifest["game"]
    identity["apworld_revision"] = manifest["world_version"]
    payload = json.dumps(identity, indent=2, sort_keys=True) + "\n"
    _write(identity_path, payload, check)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mod-root", type=Path)
    args = parser.parse_args()
    sync(check=args.check, mod_root=args.mod_root)


if __name__ == "__main__":
    main()
