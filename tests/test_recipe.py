import pytest


@pytest.fixture
def started_recipe(default_recipe):
    default_recipe.begin()
    yield default_recipe


def test_can_begin(default_recipe):
    try:
        default_recipe.begin()
    except Exception as e:
        assert False, e


def test_can_end(started_recipe):
    try:
        started_recipe.end()
    except Exception as e:
        assert False, e


def test_context_handler(default_recipe):
    try:
        with default_recipe:
            pass
    except Exception as e:
        assert False, e


def test_has_workspace(started_recipe):
    assert started_recipe.workspace.exists(), "workspace unavailable"
