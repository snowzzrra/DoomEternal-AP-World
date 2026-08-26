import settings


class DoomEternalSettings(settings.Group):
    class ClientDirectory(settings.UserFolderPath):
        """Directory where the DOOM Eternal Archipelago client is installed."""

    client_directory: ClientDirectory = ClientDirectory("~/DoomEternalArchipelago/client")
