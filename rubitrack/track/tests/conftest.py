import pytest

from track.models import Config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Le cache process-level de Config survivrait au rollback entre tests."""
    Config.clear_cache()
    yield
    Config.clear_cache()
