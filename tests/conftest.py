"""Shared fixtures for xapian_model tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from xapian_model.base import BaseXapianModel


class Product(BaseXapianModel):
    """Concrete model with template placeholders for testing."""

    INDEX_TEMPLATE = "/products/{category}"
    SCHEMA = {"name": {"_type": "text"}, "price": {"_type": "floating"}}


class SimpleModel(BaseXapianModel):
    """Concrete model with no template placeholders."""

    INDEX_TEMPLATE = "/items"
    SCHEMA = {"title": {"_type": "text"}}


@pytest.fixture()
def mock_client():
    """Patch ``xapiand.client`` and return an AsyncMock object."""
    with patch("xapian_model.base.client", new_callable=AsyncMock) as mock:
        yield mock
