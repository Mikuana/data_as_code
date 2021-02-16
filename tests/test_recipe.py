from pathlib import Path
import pytest

from data_as_code import Recipe


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


def test_destinations_are_paths(started_recipe):
    for k, v in started_recipe._destinations().items():
        assert isinstance(v, Path), f"{k} is not a path"

