"""ORM-like base classes for building models backed by Xapiand.

Provides a descriptor-based manager pattern and a base model class that
maps Python attribute access to Xapiand document fields, with automatic
schema provisioning on first write.

Example:
    >>> class Product(BaseXapianModel):
    ...     INDEX_TEMPLATE = "/products/{category}"
    ...     SCHEMA = {"name": {"_type": "text"}}
    ...
    >>> product = await Product.objects.create(category="electronics", name="Phone")
    >>> product.name
    'Phone'
"""

from __future__ import annotations

import string
from dataclasses import dataclass

from typing import Any

from xapiand import client, TransportError

_MODEL_META_PROPS = frozenset({
    '_required', '_default', '_write_only', '_read_only', '_null', '_choices',
})

_TYPE_ALIASES: dict[str, str] = {
    'json': 'object',
}

_MISSING = object()


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip model meta-properties and resolve type aliases in a schema dict.

    Returns a copy of *schema* suitable for sending to Xapiand, with
    keys in :data:`_MODEL_META_PROPS` removed from every nested dict
    and ``_type`` aliases (e.g. ``"json"`` → ``"object"``) resolved.

    Args:
        schema: The model's ``SCHEMA`` dict, potentially containing
            meta-properties like ``_required`` or ``_default``.

    Returns:
        A new dict with all meta-properties removed and type aliases
        resolved at every level.
    """
    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            field = {k: v for k, v in value.items() if k not in _MODEL_META_PROPS}
            if '_type' in field:
                field['_type'] = _TYPE_ALIASES.get(field['_type'], field['_type'])
                if field['_type'] == 'object':
                    field.setdefault('_recurse', False)
            cleaned[key] = field
        else:
            cleaned[key] = value
    return cleaned


def _extract_field_meta(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract model meta-properties from each field in the schema.

    Only processes top-level keys that do not start with ``_`` and whose
    values are dicts (i.e. field definitions).  Keys like ``_type`` or
    ``_foreign`` at the schema root are Xapiand schema properties, not
    field definitions, and are skipped.

    Args:
        schema: The model's ``SCHEMA`` dict.

    Returns:
        A dict mapping field names to their meta-properties.  Fields
        with no meta-properties are omitted.
    """
    meta: dict[str, dict[str, Any]] = {}
    for key, value in schema.items():
        if key.startswith('_') or not isinstance(value, dict):
            continue
        field_meta = {k: v for k, v in value.items() if k in _MODEL_META_PROPS}
        if field_meta:
            meta[key] = field_meta
    return meta


def _template_fields(template: str) -> set[str]:
    """Extract placeholder field names from a format-string template.

    Uses ``string.Formatter`` to parse the template and collect every
    named replacement field.

    Args:
        template: A Python format string (e.g. ``"/index/{tenant}"``).

    Returns:
        A set of field names found in the template placeholders.
    """
    return {fname for _, fname, _, _ in string.Formatter().parse(template) if fname}


@dataclass
class SearchResults:
    """Container for paginated search results from Xapiand.

    Attributes:
        results: List of model instances matching the query.
        total_count: Exact number of matching documents.
        matches_estimated: Estimated total matches (may differ from
            ``total_count`` for large result sets).
        aggregations: Optional aggregation data returned by Xapiand.
    """

    results: list[BaseXapianModel]
    total_count: int
    matches_estimated: int
    aggregations: dict | None = None


class Manager:
    """Descriptor that provides query and persistence operations for a model.

    When attached to a :class:`BaseXapianModel` subclass, it exposes
    ``create``, ``get``, and ``filter`` methods that communicate with
    the Xapiand backend.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        """Bind this manager to its owning model class.

        Called automatically by Python's descriptor protocol when the
        manager is assigned as a class attribute.

        Args:
            owner: The model class this manager is attached to.
            name: The attribute name under which the manager is stored.
        """
        self.model_cls = owner

    def _extract_index_params(self, kwargs: dict) -> dict:
        """Pop and return index-template parameters from *kwargs*.

        Inspects :attr:`model_cls.INDEX_TEMPLATE` to determine which
        keyword arguments correspond to template placeholders, removes
        them from *kwargs* in-place, and returns them separately.

        Args:
            kwargs: Mutable keyword-argument dict. Matching keys are
                removed as a side effect.

        Returns:
            A dict of extracted parameters that can be passed to
            ``INDEX_TEMPLATE.format()``.
        """
        fields = _template_fields(self.model_cls.INDEX_TEMPLATE)
        return {f: kwargs.pop(f) for f in fields if f in kwargs}

    async def create(self, *, id: str | None = None, **kwargs) -> BaseXapianModel:
        """Create a new document in Xapiand and return its model instance.

        If the index does not yet have a schema (HTTP 412), the model's
        :attr:`~BaseXapianModel.SCHEMA` is attached and the request is
        retried.

        Args:
            id: Optional document ID.  When ``None``, Xapiand generates
                one automatically.
            **kwargs: Document fields **and** index-template parameters
                (e.g. ``tenant``).  Template parameters are separated
                automatically.

        Returns:
            A new model instance populated with the stored data.

        Raises:
            TransportError: If the Xapiand request fails for reasons
                other than a missing schema.
        """
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        self.model_cls._apply_defaults(kwargs)
        self.model_cls._validate(kwargs)
        body = self.model_cls._prepare_write_body(kwargs)
        try:
            data = await client.put(index, body=body, id=id)
        except TransportError as exc:
            if exc.response.status_code == 412:
                body['_schema'] = self.model_cls._xapiand_schema
                data = await client.put(index, body=body, id=id)
            else:
                raise
        data = self.model_cls._prepare_read_data(data)
        instance = self.model_cls(data)
        instance._index_params = index_params
        return instance

    async def filter(
        self,
        *,
        query: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
        check_at_least: int | None = None,
        **kwargs,
    ) -> SearchResults:
        """Search for documents matching the given criteria.

        Args:
            query: Xapiand query string.  ``None`` matches all documents.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort: Sort expression accepted by Xapiand.
            check_at_least: Minimum number of documents to check for
                accurate count estimation.
            **kwargs: Index-template parameters and any additional
                search options.

        Returns:
            A :class:`SearchResults` instance containing matched model
            instances and pagination metadata.
        """
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        response = await client.search(
            index,
            query=query,
            limit=limit,
            offset=offset,
            sort=sort,
            check_at_least=check_at_least,
        )
        instances = []
        for hit in response.hits:
            instance = self.model_cls(self.model_cls._prepare_read_data(hit))
            instance._index_params = index_params
            instances.append(instance)
        return SearchResults(
            results=instances,
            total_count=response.count,
            matches_estimated=response.total,
            aggregations=getattr(response, 'aggregations', None),
        )

    async def get(self, *, id: str, volatile: bool = False, **kwargs) -> BaseXapianModel:
        """Retrieve a single document by its ID.

        Args:
            id: The document ID to look up.
            volatile: When ``True``, bypass Xapiand's cache and fetch
                the latest version directly from disk.
            **kwargs: Index-template parameters (e.g. ``tenant``).

        Returns:
            A model instance populated with the document data.

        Raises:
            TransportError: If the document is not found or the request
                fails.
        """
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        data = await client.get(index, id=id, volatile=volatile)
        data = self.model_cls._prepare_read_data(data)
        instance = self.model_cls(data)
        instance._index_params = index_params
        return instance


class BaseXapianModel:
    """Abstract base class for Xapiand-backed models.

    Subclasses must define :attr:`INDEX_TEMPLATE` and :attr:`SCHEMA`.
    A :class:`Manager` instance is automatically created as the ``objects``
    class attribute unless one is explicitly provided.

    Document fields are stored in an internal ``_data`` dict and exposed
    via attribute access (``__getattr__`` / ``__setattr__``).

    Example:
        >>> class Article(BaseXapianModel):
        ...     INDEX_TEMPLATE = "/articles/{language}"
        ...     SCHEMA = {"title": {"_type": "text"}}
        ...
        >>> article = Article(title="Hello")
        >>> article.title
        'Hello'

    Attributes:
        INDEX_TEMPLATE: Format string used to build the Xapiand index
            path.  May contain ``{placeholders}`` filled at runtime.
        SCHEMA: Dict describing the Xapiand schema for this model's
            fields.
        default_manager_class: The :class:`Manager` subclass used when
            auto-creating the ``objects`` descriptor.
    """

    INDEX_TEMPLATE: str
    SCHEMA: dict

    default_manager_class: type[Manager] = Manager

    def __init_subclass__(cls, **kwargs):
        """Auto-attach a manager as ``cls.objects`` on subclass creation.

        Called by Python when a new subclass of :class:`BaseXapianModel`
        is defined.  If the subclass does not explicitly declare an
        ``objects`` attribute, a new manager instance is created and
        bound to the class.

        Args:
            **kwargs: Forwarded to ``super().__init_subclass__``.
        """
        super().__init_subclass__(**kwargs)
        if 'objects' not in cls.__dict__:
            manager = cls.default_manager_class()
            manager.model_cls = cls
            cls.objects = manager
        if hasattr(cls, 'SCHEMA'):
            cls._field_meta = _extract_field_meta(cls.SCHEMA)
            cls._xapiand_schema = _clean_schema(cls.SCHEMA)
        else:
            cls._field_meta = {}
            cls._xapiand_schema = {}

    @classmethod
    def _apply_defaults(cls, data: dict) -> None:
        """Apply default values to missing fields in *data*.

        For each field in the model's meta-properties that has a
        ``_default`` entry, set the field in *data* if it is not already
        present.  Callable defaults are invoked to produce the value.

        Args:
            data: Mutable document data dict.  Modified in place.
        """
        for field, meta in cls._field_meta.items():
            if '_default' in meta and field not in data:
                default = meta['_default']
                data[field] = default() if callable(default) else default

    @classmethod
    def _validate(cls, data: dict) -> None:
        """Validate *data* against the model's meta-property constraints.

        Checks ``_required``, ``_null``, and ``_choices`` rules for every
        field that has meta-properties defined.  Also enforces the null
        constraint on schema fields that have no explicit meta-properties.

        Args:
            data: Document data dict to validate.

        Raises:
            ValueError: If any validation constraint is violated.
        """
        schema = getattr(cls, 'SCHEMA', {})
        for field, meta in cls._field_meta.items():
            if meta.get('_required') and field not in data:
                raise ValueError(f"Field {field!r} is required")
            if field in data:
                value = data[field]
                if value is None and not meta.get('_null'):
                    raise ValueError(f"Field {field!r} does not allow None")
                choices = meta.get('_choices')
                if choices is not None and value is not None and value not in choices:
                    raise ValueError(f"Field {field!r} must be one of {choices!r}, got {value!r}")
        for field, defn in schema.items():
            if field.startswith('_') or not isinstance(defn, dict):
                continue
            if field in cls._field_meta:
                continue
            if field in data and data[field] is None:
                raise ValueError(f"Field {field!r} does not allow None")

    @classmethod
    def _prepare_write_body(cls, data: dict) -> dict:
        """Return a copy of *data* with read-only fields removed.

        Fields marked ``_read_only`` in the schema are excluded from the
        dict sent to Xapiand on writes.

        Args:
            data: Document data dict.

        Returns:
            A new dict without read-only fields.
        """
        read_only = {f for f, m in cls._field_meta.items() if m.get('_read_only')}
        return {k: v for k, v in data.items() if k not in read_only}

    @classmethod
    def _prepare_read_data(cls, data: dict) -> dict:
        """Return a copy of *data* with write-only fields removed.

        Fields marked ``_write_only`` in the schema are excluded from
        the dict used to populate model instances on reads.

        Args:
            data: Document data dict returned by Xapiand.

        Returns:
            A new dict without write-only fields.
        """
        write_only = {f for f, m in cls._field_meta.items() if m.get('_write_only')}
        return {k: v for k, v in data.items() if k not in write_only}

    def __init__(self, data: dict | None = None, /, **kwargs) -> None:
        """Initialise the model instance with document data.

        Args:
            data: Initial field data as a dict.  When ``None``, an
                empty dict is used.
            **kwargs: Additional fields merged into *data*.
        """
        object.__setattr__(self, '_data', {**(data or {}), **kwargs})

    def __setattr__(self, name: str, value):
        """Set a document field or a private instance attribute.

        Names starting with ``_`` are stored directly on the instance
        (bypassing ``_data``).  All other names are written into the
        internal ``_data`` dict.

        Args:
            name: Attribute name.
            value: Value to assign.
        """
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __getattr__(self, name: str):
        """Look up a document field by name.

        Falls back to the internal ``_data`` dict for names that are
        not found via the normal attribute-resolution order.

        Args:
            name: Attribute name to look up.

        Returns:
            The field value from ``_data``.

        Raises:
            AttributeError: If *name* is not present in ``_data``.
        """
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}") from None

    def _get_index(self) -> str:
        """Build the Xapiand index path for this instance.

        Merges ``_data`` fields with any ``_index_params`` captured at
        creation time and formats :attr:`INDEX_TEMPLATE`.

        Returns:
            The fully resolved index path string.
        """
        index_params = getattr(self, '_index_params', {})
        return self.INDEX_TEMPLATE.format(**{**self._data, **index_params})

    async def save(self) -> None:
        """Persist the current document data to Xapiand.

        If the index does not yet have a schema (HTTP 412), the model's
        :attr:`SCHEMA` is included in a retry request to provision the
        schema automatically.

        Raises:
            TransportError: If the Xapiand request fails for reasons
                other than a missing schema.
        """
        index = self._get_index()
        self._apply_defaults(self._data)
        self._validate(self._data)
        body = self._prepare_write_body(self._data)
        doc_id = self._data.get('_id', self._data.get('id'))
        try:
            data = await client.put(index, body=body, id=doc_id)
        except TransportError as exc:
            if exc.response.status_code == 412:
                body['_schema'] = self._xapiand_schema
                data = await client.put(index, body=body, id=doc_id)
            else:
                raise
        self._data = self._prepare_read_data(data)

    async def delete(self) -> None:
        """Delete this document from Xapiand.

        Raises:
            TransportError: If the deletion request fails.
        """
        index = self._get_index()
        await client.delete(index, id=self._data.get('_id', self._data.get('id')))

    def __repr__(self) -> str:
        """Return a developer-friendly string representation.

        Returns:
            A string of the form ``ClassName({...data...})``.
        """
        return f"{type(self).__name__}({self._data!r})"
