"""Keep test collection and application startup away from the real database."""
import os
import tempfile

_test_data = tempfile.TemporaryDirectory(prefix='cyberant-tests-')
os.environ['APP_DATA_DIR'] = _test_data.name
os.environ['APP_ENV'] = 'development'
os.environ['APP_ORIGINS'] = 'http://testserver,http://localhost:8088,http://127.0.0.1:8088'


def pytest_unconfigure(config):
    _test_data.cleanup()
