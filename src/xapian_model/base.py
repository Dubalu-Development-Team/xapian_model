from __future__ import annotations

import string
from dataclasses import dataclass

from xapiand import client, TransportError


def _template_fields(template: str) -> set[str]:
    return {fname for _, fname, _, _ in string.Formatter().parse(template) if fname}


@dataclass
class SearchResults:
    results: list[BaseXapianModel]
    total_count: int
    matches_estimated: int
    aggregations: dict | None = None


class Manager:
    def __set_name__(self, owner: type, name: str) -> None:
        self.model_cls = owner

    def _extract_index_params(self, kwargs: dict) -> dict:
        fields = _template_fields(self.model_cls.INDEX_TEMPLATE)
        return {f: kwargs.pop(f) for f in fields if f in kwargs}

    def create(self, *, id: str | None = None, **kwargs) -> BaseXapianModel:
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        body = kwargs
        try:
            data = client.put(index, body=body, id=id)
        except TransportError as exc:
            if exc.response is not None and exc.response.status_code == 412:
                body['_schema'] = self.model_cls.SCHEMA
                data = client.put(index, body=body, id=id)
            else:
                raise
        instance = self.model_cls(data)
        instance._index_params = index_params
        return instance

    def filter(
        self,
        *,
        query: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
        check_at_least: int | None = None,
        **kwargs,
    ) -> SearchResults:
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        response = client.search(
            index,
            query=query,
            limit=limit,
            offset=offset,
            sort=sort,
            check_at_least=check_at_least,
        )
        instances = []
        for hit in response.hits:
            instance = self.model_cls(hit)
            instance._index_params = index_params
            instances.append(instance)
        return SearchResults(
            results=instances,
            total_count=response.count,
            matches_estimated=response.total,
            aggregations=getattr(response, 'aggregations', None),
        )

    def get(self, *, id: str, volatile: bool = False, **kwargs) -> BaseXapianModel:
        index_params = self._extract_index_params(kwargs)
        index = self.model_cls.INDEX_TEMPLATE.format(**index_params)
        data = client.get(index, id=id, volatile=volatile)
        instance = self.model_cls(data)
        instance._index_params = index_params
        return instance


class BaseXapianModel:
    INDEX_TEMPLATE: str
    SCHEMA: dict

    default_manager_class: type[Manager] = Manager

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'objects' not in cls.__dict__:
            manager = cls.default_manager_class()
            manager.model_cls = cls
            cls.objects = manager

    def __init__(self, data: dict | None = None, /, **kwargs) -> None:
        object.__setattr__(self, '_data', {**(data or {}), **kwargs})

    def __setattr__(self, name: str, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __getattr__(self, name: str):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}") from None

    def _get_index(self) -> str:
        index_params = getattr(self, '_index_params', {})
        return self.INDEX_TEMPLATE.format(**{**self._data, **index_params})

    def save(self) -> None:
        index = self._get_index()
        body = self._data
        try:
            data = client.put(index, body=body, id=body.get('id'))
        except TransportError as exc:
            if exc.response is not None and exc.response.status_code == 412:
                body = {**self._data, '_schema': self.SCHEMA}
                data = client.put(index, body=body, id=body.get('id'))
            else:
                raise
        self._data = data

    def delete(self) -> None:
        index = self._get_index()
        client.delete(index, id=self._data.get('id'))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"
