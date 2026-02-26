"""Tests for xapian_model.base — targeting 100% coverage."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from xapian_model.base import (
    BaseXapianModel,
    Manager,
    SearchResults,
    TransportError,
    _clean_schema,
    _extract_field_meta,
    _template_fields,
)

from .conftest import Product, SimpleModel, ValidatedModel


# ---------------------------------------------------------------------------
# _template_fields
# ---------------------------------------------------------------------------


class TestTemplateFields:
    """Tests for the _template_fields helper."""

    def test_named_fields(self):
        result = _template_fields("/index/{tenant}/{region}")
        assert result == {"tenant", "region"}

    def test_no_placeholders(self):
        result = _template_fields("/static/index")
        assert result == set()


# ---------------------------------------------------------------------------
# SearchResults dataclass
# ---------------------------------------------------------------------------


class TestSearchResults:
    """Tests for the SearchResults dataclass."""

    def test_construction_with_all_fields(self):
        sr = SearchResults(
            results=["a", "b"],
            total_count=10,
            matches_estimated=15,
            aggregations={"avg_price": 42},
        )
        assert sr.results == ["a", "b"]
        assert sr.total_count == 10
        assert sr.matches_estimated == 15
        assert sr.aggregations == {"avg_price": 42}

    def test_default_aggregations_is_none(self):
        sr = SearchResults(results=[], total_count=0, matches_estimated=0)
        assert sr.aggregations is None


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class TestManagerSetName:
    """Tests for Manager.__set_name__."""

    def test_binds_model_cls(self):
        manager = Manager()
        manager.__set_name__(Product, "objects")
        assert manager.model_cls is Product


class TestManagerExtractIndexParams:
    """Tests for Manager._extract_index_params."""

    def test_extracts_template_fields(self):
        kwargs = {"category": "electronics", "name": "Phone"}
        params = Product.objects._extract_index_params(kwargs)
        assert params == {"category": "electronics"}
        assert kwargs == {"name": "Phone"}

    def test_no_template_fields_present(self):
        kwargs = {"name": "Phone"}
        params = Product.objects._extract_index_params(kwargs)
        assert params == {}
        assert kwargs == {"name": "Phone"}


class TestManagerCreate:
    """Tests for Manager.create."""

    @pytest.mark.asyncio
    async def test_happy_path(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Phone", "category": "electronics"}
        product = await Product.objects.create(category="electronics", name="Phone")

        mock_client.put.assert_called_once_with("/products/electronics", body={"name": "Phone"}, id=None)
        assert isinstance(product, Product)
        assert product.name == "Phone"
        assert product._index_params == {"category": "electronics"}

    @pytest.mark.asyncio
    async def test_with_explicit_id(self, mock_client):
        mock_client.put.return_value = {"id": "abc", "name": "Phone"}
        product = await Product.objects.create(id="abc", category="electronics", name="Phone")

        mock_client.put.assert_called_once_with("/products/electronics", body={"name": "Phone"}, id="abc")
        assert product.id == "abc"

    @pytest.mark.asyncio
    async def test_schema_auto_provision_on_412(self, mock_client):
        response_412 = MagicMock()
        response_412.status_code = 412
        exc = TransportError("Precondition Failed", request=MagicMock(), response=response_412)
        mock_client.put.side_effect = [exc, {"id": "1", "name": "Phone"}]

        product = await Product.objects.create(category="electronics", name="Phone")

        assert mock_client.put.call_count == 2
        second_call_body = mock_client.put.call_args_list[1][1]["body"]
        assert "_schema" in second_call_body
        assert second_call_body["_schema"] == Product._xapiand_schema
        assert isinstance(product, Product)

    @pytest.mark.asyncio
    async def test_reraise_on_non_412(self, mock_client):
        response_500 = MagicMock()
        response_500.status_code = 500
        exc = TransportError("Internal Server Error", request=MagicMock(), response=response_500)
        mock_client.put.side_effect = exc

        with pytest.raises(TransportError):
            await Product.objects.create(category="electronics", name="Phone")


class TestManagerFilter:
    """Tests for Manager.filter."""

    @pytest.mark.asyncio
    async def test_returns_search_results(self, mock_client):
        response = MagicMock()
        response.hits = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        response.count = 2
        response.total = 100
        response.aggregations = {"avg": 5}
        mock_client.search.return_value = response

        result = await Product.objects.filter(category="electronics", query="*", limit=10)

        mock_client.search.assert_called_once_with(
            "/products/electronics",
            query="*",
            limit=10,
            offset=None,
            sort=None,
            check_at_least=None,
        )
        assert isinstance(result, SearchResults)
        assert len(result.results) == 2
        assert all(isinstance(r, Product) for r in result.results)
        assert result.total_count == 2
        assert result.matches_estimated == 100
        assert result.aggregations == {"avg": 5}

    @pytest.mark.asyncio
    async def test_no_aggregations_attribute(self, mock_client):
        response = MagicMock(spec=["hits", "count", "total"])
        response.hits = []
        response.count = 0
        response.total = 0
        mock_client.search.return_value = response

        result = await Product.objects.filter(category="electronics")
        assert result.aggregations is None


class TestManagerGet:
    """Tests for Manager.get."""

    @pytest.mark.asyncio
    async def test_happy_path(self, mock_client):
        mock_client.get.return_value = {"id": "42", "name": "Widget"}
        product = await Product.objects.get(id="42", category="electronics")

        mock_client.get.assert_called_once_with("/products/electronics", id="42", volatile=False)
        assert isinstance(product, Product)
        assert product.name == "Widget"
        assert product._index_params == {"category": "electronics"}

    @pytest.mark.asyncio
    async def test_volatile(self, mock_client):
        mock_client.get.return_value = {"id": "42", "name": "Widget"}
        await Product.objects.get(id="42", category="electronics", volatile=True)

        mock_client.get.assert_called_once_with("/products/electronics", id="42", volatile=True)


# ---------------------------------------------------------------------------
# BaseXapianModel.__init_subclass__
# ---------------------------------------------------------------------------


class TestInitSubclass:
    """Tests for BaseXapianModel.__init_subclass__."""

    def test_auto_creates_objects_manager(self):
        assert hasattr(Product, "objects")
        assert isinstance(Product.objects, Manager)
        assert Product.objects.model_cls is Product

    def test_skips_when_objects_explicitly_defined(self):
        custom_manager = Manager()

        class Custom(BaseXapianModel):
            INDEX_TEMPLATE = "/custom"
            SCHEMA = {}
            objects = custom_manager

        assert Custom.objects is custom_manager

    def test_custom_default_manager_class(self):
        class SpecialManager(Manager):
            pass

        class Special(BaseXapianModel):
            INDEX_TEMPLATE = "/special"
            SCHEMA = {}
            default_manager_class = SpecialManager

        assert isinstance(Special.objects, SpecialManager)


# ---------------------------------------------------------------------------
# BaseXapianModel.__init__
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for BaseXapianModel.__init__."""

    def test_with_data_dict(self):
        p = Product({"name": "Phone", "price": 99})
        assert p._data == {"name": "Phone", "price": 99}

    def test_with_none_data(self):
        p = Product(None)
        assert p._data == {}

    def test_no_args(self):
        p = Product()
        assert p._data == {}

    def test_with_kwargs(self):
        p = Product(name="Phone")
        assert p._data == {"name": "Phone"}

    def test_data_and_kwargs_merged(self):
        p = Product({"name": "Phone", "price": 50}, price=99)
        assert p._data == {"name": "Phone", "price": 99}


# ---------------------------------------------------------------------------
# BaseXapianModel.__setattr__ / __getattr__
# ---------------------------------------------------------------------------


class TestSetattr:
    """Tests for BaseXapianModel.__setattr__."""

    def test_private_attr_stored_on_instance(self):
        p = Product()
        p._custom = "private"
        assert p.__dict__["_custom"] == "private"

    def test_public_attr_stored_in_data(self):
        p = Product()
        p.name = "Phone"
        assert p._data["name"] == "Phone"


class TestGetattr:
    """Tests for BaseXapianModel.__getattr__."""

    def test_existing_field(self):
        p = Product({"name": "Phone"})
        assert p.name == "Phone"

    def test_missing_field_raises(self):
        p = Product()
        with pytest.raises(AttributeError, match="'Product' object has no attribute 'missing'"):
            p.missing


# ---------------------------------------------------------------------------
# BaseXapianModel._get_index
# ---------------------------------------------------------------------------


class TestGetIndex:
    """Tests for BaseXapianModel._get_index."""

    def test_with_index_params(self):
        p = Product({"name": "Phone"})
        p._index_params = {"category": "electronics"}
        assert p._get_index() == "/products/electronics"

    def test_without_index_params_uses_data(self):
        p = Product({"category": "books", "name": "Novel"})
        assert p._get_index() == "/products/books"


# ---------------------------------------------------------------------------
# BaseXapianModel.save
# ---------------------------------------------------------------------------


class TestSave:
    """Tests for BaseXapianModel.save."""

    @pytest.mark.asyncio
    async def test_happy_path(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Updated"}
        p = SimpleModel({"id": "1", "title": "Old"})
        await p.save()

        mock_client.put.assert_called_once_with("/items", body={"id": "1", "title": "Old"}, id="1")
        assert p._data == {"id": "1", "name": "Updated"}

    @pytest.mark.asyncio
    async def test_schema_auto_provision_on_412(self, mock_client):
        response_412 = MagicMock()
        response_412.status_code = 412
        exc = TransportError("Precondition Failed", request=MagicMock(), response=response_412)
        mock_client.put.side_effect = [exc, {"id": "1", "title": "Saved"}]

        p = SimpleModel({"id": "1", "title": "New"})
        await p.save()

        assert mock_client.put.call_count == 2
        second_body = mock_client.put.call_args_list[1][1]["body"]
        assert second_body["_schema"] == SimpleModel._xapiand_schema
        assert p._data == {"id": "1", "title": "Saved"}

    @pytest.mark.asyncio
    async def test_reraise_on_non_412(self, mock_client):
        response_500 = MagicMock()
        response_500.status_code = 500
        exc = TransportError("Internal Server Error", request=MagicMock(), response=response_500)
        mock_client.put.side_effect = exc

        p = SimpleModel({"id": "1", "title": "New"})
        with pytest.raises(TransportError):
            await p.save()


# ---------------------------------------------------------------------------
# BaseXapianModel.delete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for BaseXapianModel.delete."""

    @pytest.mark.asyncio
    async def test_calls_client_delete(self, mock_client):
        p = SimpleModel({"id": "42", "title": "Doomed"})
        await p.delete()

        mock_client.delete.assert_called_once_with("/items", id="42")


# ---------------------------------------------------------------------------
# BaseXapianModel.__repr__
# ---------------------------------------------------------------------------


class TestRepr:
    """Tests for BaseXapianModel.__repr__."""

    def test_repr(self):
        p = Product({"name": "Phone"})
        assert repr(p) == "Product({'name': 'Phone'})"


# ---------------------------------------------------------------------------
# _clean_schema
# ---------------------------------------------------------------------------


class TestCleanSchema:
    """Tests for the _clean_schema helper."""

    def test_strips_meta_props(self):
        schema = {
            "name": {"_type": "text", "_required": True, "_default": ""},
            "role": {"_type": "keyword", "_choices": ["admin", "user"]},
        }
        cleaned = _clean_schema(schema)
        assert cleaned == {
            "name": {"_type": "text"},
            "role": {"_type": "keyword"},
        }

    def test_preserves_xapiand_props(self):
        schema = {
            "_type": "object",
            "name": {"_type": "text", "_required": True},
        }
        cleaned = _clean_schema(schema)
        assert cleaned["_type"] == "object"
        assert cleaned["name"] == {"_type": "text"}

    def test_resolves_json_type_alias(self):
        schema = {"metadata": {"_type": "json", "_required": True}}
        cleaned = _clean_schema(schema)
        assert cleaned == {"metadata": {"_type": "object"}}

    def test_preserves_non_aliased_types(self):
        schema = {"name": {"_type": "text"}}
        cleaned = _clean_schema(schema)
        assert cleaned["name"]["_type"] == "text"

    def test_preserves_non_dict_values(self):
        schema = {"_type": "object", "name": {"_type": "text"}}
        cleaned = _clean_schema(schema)
        assert cleaned == schema


# ---------------------------------------------------------------------------
# _extract_field_meta
# ---------------------------------------------------------------------------


class TestExtractFieldMeta:
    """Tests for the _extract_field_meta helper."""

    def test_extracts_meta_per_field(self):
        meta = _extract_field_meta(ValidatedModel.SCHEMA)
        assert meta["name"] == {"_required": True}
        assert meta["email"] == {"_default": ""}
        assert meta["role"] == {"_choices": ["admin", "user"]}
        assert meta["score"] == {"_null": True}
        assert meta["password"] == {"_write_only": True}
        assert meta["created_at"] == {"_read_only": True}

    def test_skips_underscore_keys(self):
        schema = {"_type": "object", "name": {"_type": "text", "_required": True}}
        meta = _extract_field_meta(schema)
        assert "_type" not in meta
        assert "name" in meta

    def test_skips_non_dict_values(self):
        schema = {"version": 1, "name": {"_type": "text", "_required": True}}
        meta = _extract_field_meta(schema)
        assert "version" not in meta

    def test_skips_fields_without_meta(self):
        schema = {"title": {"_type": "text"}}
        meta = _extract_field_meta(schema)
        assert meta == {}


# ---------------------------------------------------------------------------
# _apply_defaults
# ---------------------------------------------------------------------------


class TestApplyDefaults:
    """Tests for BaseXapianModel._apply_defaults."""

    def test_applies_static_default(self):
        data = {"name": "Alice"}
        ValidatedModel._apply_defaults(data)
        assert data["email"] == ""

    def test_does_not_overwrite_existing(self):
        data = {"name": "Alice", "email": "alice@example.com"}
        ValidatedModel._apply_defaults(data)
        assert data["email"] == "alice@example.com"

    def test_callable_default(self):
        class CallableDefaultModel(BaseXapianModel):
            INDEX_TEMPLATE = "/callable"
            SCHEMA = {"tags": {"_type": "array", "_default": list}}

        data = {}
        CallableDefaultModel._apply_defaults(data)
        assert data["tags"] == []
        data2 = {}
        CallableDefaultModel._apply_defaults(data2)
        assert data2["tags"] is not data["tags"]


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------


class TestValidate:
    """Tests for BaseXapianModel._validate."""

    def test_required_missing_raises(self):
        with pytest.raises(ValueError, match="'name' is required"):
            ValidatedModel._validate({"email": "x"})

    def test_required_present_ok(self):
        ValidatedModel._validate({"name": "Alice"})

    def test_null_disallowed_raises(self):
        with pytest.raises(ValueError, match="'name' does not allow None"):
            ValidatedModel._validate({"name": None})

    def test_null_allowed_ok(self):
        ValidatedModel._validate({"name": "Alice", "score": None})

    def test_choices_invalid_raises(self):
        with pytest.raises(ValueError, match="'role' must be one of"):
            ValidatedModel._validate({"name": "Alice", "role": "superadmin"})

    def test_choices_valid_ok(self):
        ValidatedModel._validate({"name": "Alice", "role": "admin"})

    def test_choices_none_with_null_skips(self):
        """When value is None and _null is set, choices check is skipped."""
        class NullChoiceModel(BaseXapianModel):
            INDEX_TEMPLATE = "/nc"
            SCHEMA = {"status": {"_type": "keyword", "_null": True, "_choices": ["a", "b"]}}

        NullChoiceModel._validate({"status": None})

    def test_schema_field_without_meta_null_raises(self):
        """Fields in schema without explicit meta still reject None."""
        class PlainModel(BaseXapianModel):
            INDEX_TEMPLATE = "/plain"
            SCHEMA = {"title": {"_type": "text"}}

        with pytest.raises(ValueError, match="'title' does not allow None"):
            PlainModel._validate({"title": None})


# ---------------------------------------------------------------------------
# _prepare_write_body
# ---------------------------------------------------------------------------


class TestPrepareWriteBody:
    """Tests for BaseXapianModel._prepare_write_body."""

    def test_excludes_read_only(self):
        data = {"name": "Alice", "created_at": "2025-01-01T00:00:00"}
        body = ValidatedModel._prepare_write_body(data)
        assert "created_at" not in body
        assert body["name"] == "Alice"

    def test_keeps_write_only(self):
        data = {"name": "Alice", "password": "secret"}
        body = ValidatedModel._prepare_write_body(data)
        assert body["password"] == "secret"


# ---------------------------------------------------------------------------
# _prepare_read_data
# ---------------------------------------------------------------------------


class TestPrepareReadData:
    """Tests for BaseXapianModel._prepare_read_data."""

    def test_excludes_write_only(self):
        data = {"name": "Alice", "password": "secret"}
        result = ValidatedModel._prepare_read_data(data)
        assert "password" not in result
        assert result["name"] == "Alice"

    def test_keeps_read_only(self):
        data = {"name": "Alice", "created_at": "2025-01-01T00:00:00"}
        result = ValidatedModel._prepare_read_data(data)
        assert result["created_at"] == "2025-01-01T00:00:00"


# ---------------------------------------------------------------------------
# __init_subclass__ meta-property computation
# ---------------------------------------------------------------------------


class TestInitSubclassMetaProps:
    """Tests for meta-property computation in __init_subclass__."""

    def test_xapiand_schema_strips_meta(self):
        assert "_required" not in ValidatedModel._xapiand_schema["name"]
        assert ValidatedModel._xapiand_schema["name"] == {"_type": "text"}

    def test_field_meta_populated(self):
        assert "name" in ValidatedModel._field_meta
        assert ValidatedModel._field_meta["name"]["_required"] is True

    def test_no_schema_gives_empty(self):
        class NoSchema(BaseXapianModel):
            INDEX_TEMPLATE = "/no"

        assert NoSchema._field_meta == {}
        assert NoSchema._xapiand_schema == {}

    def test_json_type_alias_resolved_in_xapiand_schema(self):
        class JsonModel(BaseXapianModel):
            INDEX_TEMPLATE = "/json"
            SCHEMA = {"payload": {"_type": "json", "_required": True}}

        assert JsonModel._xapiand_schema["payload"]["_type"] == "object"


# ---------------------------------------------------------------------------
# Integration: create with validation
# ---------------------------------------------------------------------------


class TestCreateWithValidation:
    """Integration tests for Manager.create with meta-properties."""

    @pytest.mark.asyncio
    async def test_defaults_applied(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "email": ""}
        instance = await ValidatedModel.objects.create(name="Alice")
        body = mock_client.put.call_args[1]["body"]
        assert body.get("email") == ""

    @pytest.mark.asyncio
    async def test_validation_rejects_missing_required(self, mock_client):
        with pytest.raises(ValueError, match="'name' is required"):
            await ValidatedModel.objects.create(email="x@example.com")

    @pytest.mark.asyncio
    async def test_read_only_stripped_from_write(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "created_at": "2025-01-01"}
        await ValidatedModel.objects.create(name="Alice", created_at="2025-01-01")
        body = mock_client.put.call_args[1]["body"]
        assert "created_at" not in body

    @pytest.mark.asyncio
    async def test_write_only_stripped_from_read(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "password": "hashed"}
        instance = await ValidatedModel.objects.create(name="Alice", password="secret")
        assert "password" not in instance._data

    @pytest.mark.asyncio
    async def test_412_uses_xapiand_schema(self, mock_client):
        response_412 = MagicMock()
        response_412.status_code = 412
        exc = TransportError("Precondition Failed", request=MagicMock(), response=response_412)
        mock_client.put.side_effect = [exc, {"id": "1", "name": "Alice"}]

        await ValidatedModel.objects.create(name="Alice")
        second_body = mock_client.put.call_args_list[1][1]["body"]
        assert second_body["_schema"] == ValidatedModel._xapiand_schema
        assert "_required" not in second_body["_schema"]["name"]


# ---------------------------------------------------------------------------
# Integration: save with validation
# ---------------------------------------------------------------------------


class TestSaveWithValidation:
    """Integration tests for BaseXapianModel.save with meta-properties."""

    @pytest.mark.asyncio
    async def test_defaults_applied_on_save(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "email": ""}
        instance = ValidatedModel({"id": "1", "name": "Alice"})
        await instance.save()
        body = mock_client.put.call_args[1]["body"]
        assert body.get("email") == ""

    @pytest.mark.asyncio
    async def test_validation_rejects_on_save(self, mock_client):
        instance = ValidatedModel({"id": "1"})
        with pytest.raises(ValueError, match="'name' is required"):
            await instance.save()

    @pytest.mark.asyncio
    async def test_read_only_stripped_on_save(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "created_at": "2025-01-01"}
        instance = ValidatedModel({"id": "1", "name": "Alice", "created_at": "2025-01-01"})
        await instance.save()
        body = mock_client.put.call_args[1]["body"]
        assert "created_at" not in body

    @pytest.mark.asyncio
    async def test_write_only_stripped_after_save(self, mock_client):
        mock_client.put.return_value = {"id": "1", "name": "Alice", "password": "hashed"}
        instance = ValidatedModel({"id": "1", "name": "Alice", "password": "secret"})
        await instance.save()
        assert "password" not in instance._data

    @pytest.mark.asyncio
    async def test_412_uses_xapiand_schema_on_save(self, mock_client):
        response_412 = MagicMock()
        response_412.status_code = 412
        exc = TransportError("Precondition Failed", request=MagicMock(), response=response_412)
        mock_client.put.side_effect = [exc, {"id": "1", "name": "Alice"}]

        instance = ValidatedModel({"id": "1", "name": "Alice"})
        await instance.save()
        second_body = mock_client.put.call_args_list[1][1]["body"]
        assert second_body["_schema"] == ValidatedModel._xapiand_schema


# ---------------------------------------------------------------------------
# Integration: get/filter with filtering
# ---------------------------------------------------------------------------


class TestGetWithFiltering:
    """Integration tests for read-side filtering on get and filter."""

    @pytest.mark.asyncio
    async def test_get_strips_write_only(self, mock_client):
        mock_client.get.return_value = {"id": "1", "name": "Alice", "password": "hashed"}
        instance = await ValidatedModel.objects.get(id="1")
        assert "password" not in instance._data
        assert instance.name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_strips_write_only(self, mock_client):
        response = MagicMock()
        response.hits = [{"id": "1", "name": "Alice", "password": "hashed"}]
        response.count = 1
        response.total = 1
        response.aggregations = None
        mock_client.search.return_value = response

        result = await ValidatedModel.objects.filter(query="*")
        assert "password" not in result.results[0]._data
