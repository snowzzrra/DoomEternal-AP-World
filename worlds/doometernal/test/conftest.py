def pytest_configure(config):
    config.addinivalue_line("markers", "slow: broad generation and fill regressions")


def pytest_sessionstart(session):
    import Utils

    import settings

    root = session.config._tmp_path_factory.getbasetemp() / "ap-user"
    root.mkdir()
    Utils.user_path.cached_path = str(root)
    settings.skip_autosave = True
    settings.get_settings._cache = settings.Settings(None)
