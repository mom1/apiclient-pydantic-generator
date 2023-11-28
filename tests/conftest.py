from pathlib import Path

import pytest


@pytest.fixture
def resources_folder():
    return Path(__file__).parent / "resources"
