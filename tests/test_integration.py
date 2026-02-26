"""Integration tests against a running Xapiand server.

Requires ``XAPIAND_HOST`` (default 127.0.0.1) on port 8880.
Run with: ``python -m pytest tests/test_integration.py -v``
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from xapiand import NotFoundError
from xapian_model.base import BaseXapianModel, SearchResults


# ---------------------------------------------------------------------------
# Unique run ID so parallel runs don't collide
# ---------------------------------------------------------------------------

RUN_ID = uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Test models (mirrors the README pattern with foreign schemas)
# ---------------------------------------------------------------------------


class Product(BaseXapianModel):
    """Product model following the README pattern with foreign schema."""

    INDEX_TEMPLATE = f"/test_integ_{RUN_ID}/products/{{category}}"
    SCHEMA = {
        "_type": "foreign/object",
        "_foreign": f"/schemas/test_integ_{RUN_ID}_product",
        "name": {"_type": "text"},
        "price": {"_type": "float"},
        "tags": {"_type": "keyword"},
    }


class ValidatedProduct(BaseXapianModel):
    """Product model with meta-properties for validation testing."""

    INDEX_TEMPLATE = f"/test_integ_{RUN_ID}/validated/{{category}}"
    SCHEMA = {
        "_type": "foreign/object",
        "_foreign": f"/schemas/test_integ_{RUN_ID}_validated",
        "name": {"_type": "text", "_required": True},
        "price": {"_type": "float", "_default": 0.0},
        "role": {"_type": "keyword", "_choices": ["featured", "standard"]},
        "internal_code": {"_type": "keyword", "_write_only": True},
        "created_at": {"_type": "keyword", "_read_only": True},
    }


# ---------------------------------------------------------------------------
# Shared event loop for the entire module — avoids the stale-session
# problem caused by the class-level httpx.AsyncClient in pyxapiand.
# ---------------------------------------------------------------------------

_loop = asyncio.new_event_loop()


def run(coro):
    """Run an async coroutine on the module-shared event loop."""
    return _loop.run_until_complete(coro)


@pytest.fixture(autouse=True, scope="module")
def _close_loop_at_end():
    """Close the shared event loop after all tests in the module finish."""
    yield
    _loop.close()


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestCreate:
    """Test creating documents via Manager.create."""

    def test_create_returns_instance(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(Product.objects.create(
            category="electronics",
            id=doc_id,
            name="Smartphone X",
            price=599.99,
            tags="mobile",
        ))
        assert isinstance(p, Product)
        assert p.name == "Smartphone X"
        assert p.price == 599.99
        run(p.delete())


class TestGet:
    """Test retrieving documents via Manager.get."""

    def test_get_by_id(self):
        doc_id = uuid.uuid4().hex[:12]
        run(Product.objects.create(
            category="get_test",
            id=doc_id,
            name="Widget",
            price=9.99,
            tags="gadget",
        ))
        fetched = run(Product.objects.get(
            id=doc_id, category="get_test", volatile=True,
        ))
        assert fetched.name == "Widget"
        assert fetched.price == 9.99
        run(fetched.delete())


class TestSave:
    """Test updating documents via instance.save()."""

    def test_update_field_and_save(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(Product.objects.create(
            category="save_test",
            id=doc_id,
            name="Old Name",
            price=10.0,
            tags="tag",
        ))
        p.price = 25.0
        run(p.save())

        reloaded = run(Product.objects.get(
            id=doc_id, category="save_test", volatile=True,
        ))
        assert reloaded.price == 25.0
        run(reloaded.delete())


class TestDelete:
    """Test deleting documents."""

    def test_delete_removes_document(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(Product.objects.create(
            category="del_test",
            id=doc_id,
            name="To Delete",
            price=1.0,
            tags="tmp",
        ))
        run(p.delete())

        with pytest.raises(NotFoundError):
            run(Product.objects.get(
                id=doc_id, category="del_test", volatile=True,
            ))


class TestFilter:
    """Test searching documents via Manager.filter."""

    def test_filter_returns_search_results(self):
        from xapiand import client as xapiand_client

        # Temporarily enable commit so documents are immediately searchable.
        old_commit = xapiand_client.commit
        xapiand_client.commit = True
        try:
            created = []
            for i in range(3):
                p = run(Product.objects.create(
                    category="filter_test",
                    id=f"filter-{RUN_ID}-{i}",
                    name=f"Book {i}",
                    price=float(i + 1),
                    tags="fiction",
                ))
                created.append(p)
        finally:
            xapiand_client.commit = old_commit

        results = run(Product.objects.filter(
            category="filter_test",
            query="*",
            limit=10,
        ))
        assert isinstance(results, SearchResults)
        assert results.total_count >= 3

        for p in created:
            run(p.delete())


# ---------------------------------------------------------------------------
# Meta-property integration tests
# ---------------------------------------------------------------------------


class TestValidationIntegration:
    """Test meta-properties against the real server."""

    def test_default_applied(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(ValidatedProduct.objects.create(
            category="defaults",
            id=doc_id,
            name="Defaulted",
        ))
        reloaded = run(ValidatedProduct.objects.get(
            id=doc_id, category="defaults", volatile=True,
        ))
        assert reloaded.price == 0.0
        run(p.delete())

    def test_required_rejected_before_server(self):
        with pytest.raises(ValueError, match="'name' is required"):
            run(ValidatedProduct.objects.create(
                category="validation",
                price=5.0,
            ))

    def test_choices_rejected_before_server(self):
        with pytest.raises(ValueError, match="'role' must be one of"):
            run(ValidatedProduct.objects.create(
                category="validation",
                name="Bad Role",
                role="superadmin",
            ))

    def test_null_rejected_for_non_nullable(self):
        with pytest.raises(ValueError, match="'name' does not allow None"):
            run(ValidatedProduct.objects.create(
                category="validation",
                name=None,
            ))

    def test_write_only_stripped_on_read(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(ValidatedProduct.objects.create(
            category="write_only",
            id=doc_id,
            name="Secret",
            internal_code="XYZ-999",
        ))
        assert "internal_code" not in p._data

        fetched = run(ValidatedProduct.objects.get(
            id=doc_id, category="write_only", volatile=True,
        ))
        assert "internal_code" not in fetched._data
        run(p.delete())

    def test_read_only_stripped_on_write(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(ValidatedProduct.objects.create(
            category="read_only",
            id=doc_id,
            name="ReadOnly test",
            created_at="2025-01-01",
        ))
        assert isinstance(p, ValidatedProduct)
        run(p.delete())

    def test_save_validates(self):
        doc_id = uuid.uuid4().hex[:12]
        p = run(ValidatedProduct.objects.create(
            category="save_val",
            id=doc_id,
            name="Will break",
        ))
        p.name = None
        with pytest.raises(ValueError, match="'name' does not allow None"):
            run(p.save())
        p.name = "Fixed"
        run(p.save())
        run(p.delete())

    def test_xapiand_schema_has_no_meta_props(self):
        schema = ValidatedProduct._xapiand_schema
        for field_name, defn in schema.items():
            if isinstance(defn, dict):
                for key in defn:
                    assert not key.startswith("_") or key == "_type", (
                        f"Meta-prop {key!r} leaked into _xapiand_schema[{field_name!r}]"
                    )
