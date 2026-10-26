import os
import tempfile
import pytest


@pytest.fixture
def tmp_db():
    """Cria um arquivo SQLite temporário e retorna o path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
