"""GENESIS Tests Package"""

import pytest


# 测试配置
def pytest_configure(config):
    """配置 pytest markers。"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "gpu: marks tests that require GPU")
    config.addinivalue_line("markers", "integration: marks integration tests")
