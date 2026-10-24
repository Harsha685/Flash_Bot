import pytest

from flashbot.workspace import Workspace, set_workspace


@pytest.fixture
def ws(tmp_path):
    """A fresh, active workspace for each test."""
    workspace = Workspace(tmp_path).ensure()
    set_workspace(workspace)
    yield workspace
    set_workspace(None)


def write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
