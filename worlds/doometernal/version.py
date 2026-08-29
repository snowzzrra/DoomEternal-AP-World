"""Runtime identity derived from official APWorld and generated content metadata."""

import json
from importlib.resources import files
from typing import cast

from .generated_content import (
    BRIDGE_PROTOCOL_VERSION,
    CONTENT_SCHEMA_VERSION,
)
from .generated_content import (
    COMPILER_REVISION as GENERATED_COMPILER_REVISION,
)
from .generated_content import (
    CONTENT_REVISION as GENERATED_CONTENT_REVISION,
)
from .generated_content import SESSION_MOD_CONTRACT_REVISION

_manifest = json.loads(files(__package__).joinpath("archipelago.json").read_text(encoding="utf-8"))

GAME_NAME = cast(str, _manifest["game"])
PUBLIC_VERSION = cast(str, _manifest["world_version"])
APWORLD_REVISION = PUBLIC_VERSION
CONTENT_REVISION = GENERATED_CONTENT_REVISION
BRIDGE_PROTOCOL = BRIDGE_PROTOCOL_VERSION
CONTENT_SCHEMA = CONTENT_SCHEMA_VERSION
COMPILER_REVISION = GENERATED_COMPILER_REVISION

SLOT_DATA_SCHEMA_VERSION = 4
SLOT_DATA_REVISION = "0.5-D"
ROOM_CONTRACT_REVISION = SESSION_MOD_CONTRACT_REVISION
