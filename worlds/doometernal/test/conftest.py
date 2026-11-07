def pytest_configure(config):
    config.addinivalue_line("markers", "slow: broad generation and fill regressions")
