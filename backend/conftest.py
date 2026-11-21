"""Fixtures for every test."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _empty_cache():
    """Each test starts with an empty cache, so API rate limits never carry over."""
    cache.clear()
