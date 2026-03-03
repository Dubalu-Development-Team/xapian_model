"""Shared fixtures for xapian_model tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from xapian_model.base import BaseXapianModel


class Product(BaseXapianModel):
    """Concrete model with template placeholders for testing."""

    INDEX_TEMPLATE = "/test/products/{category}"
    SCHEMA = {"name": {"_type": "text"}, "price": {"_type": "floating"}}


class SimpleModel(BaseXapianModel):
    """Concrete model with no template placeholders."""

    INDEX_TEMPLATE = "/test/items"
    SCHEMA = {"title": {"_type": "text"}}


class ValidatedModel(BaseXapianModel):
    """Concrete model with meta-properties for validation testing."""

    INDEX_TEMPLATE = "/test/validated"
    SCHEMA = {
        "name": {"_type": "text", "_required": True},
        "email": {"_type": "text", "_default": ""},
        "role": {"_type": "keyword", "_choices": ["admin", "user"]},
        "score": {"_type": "floating", "_null": True},
        "password": {"_type": "text", "_write_only": True},
        "created_at": {"_type": "datetime", "_read_only": True},
    }


@pytest.fixture()
def mock_client():
    """Patch ``xapiand.client`` and return an AsyncMock object."""
    with patch("xapian_model.base.client", new_callable=AsyncMock) as mock:
        yield mock
