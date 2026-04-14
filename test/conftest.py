"""Shared pytest fixtures for the levv test suite."""

import importlib.machinery
import importlib.util
import pathlib
import pytest


@pytest.fixture(scope='session')
def levv_bin():
    """Import bin/levv as a module.

    bin/levv has no .py extension, so we must supply a SourceFileLoader
    explicitly — spec_from_file_location returns None without one.
    """
    path = str(pathlib.Path(__file__).parent.parent / 'bin' / 'levv')
    loader = importlib.machinery.SourceFileLoader('levv_bin', path)
    spec = importlib.util.spec_from_loader('levv_bin', loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod
