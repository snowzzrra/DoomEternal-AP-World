import settings

from .player_strings_generated import text as player_text


class DoomEternalSettings(settings.Group):
    class ClientDirectory(settings.UserFolderPath):
        __doc__ = player_text("apworld.settings", "client_directory")

    client_directory: ClientDirectory = ClientDirectory("~/DoomEternalArchipelago/client")
