import os
import sys
import tempfile
import pytest

# Add agente-financeiro directory to path so tests can import database directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agente-financeiro"))


@pytest.fixture
def tmp_db():
    """Cria um arquivo SQLite temporário e retorna o path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
