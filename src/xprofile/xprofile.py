from __future__ import annotations

from dataclasses import dataclass

from xapiand import client, TransportError

from .schemas import PROFILES_ADMIN_API, PROFILE_SCHEMA, get_profile_schema


@dataclass
class SearchResults:
    results: list[XProfile]
    total_count: int
    matches_estimated: int
    aggregations: dict | None = None


class Manager:
    def __set_name__(self, owner: type, name: str) -> None:
        self.model_cls = owner

    def create(self, entity_id: str, id: str, **kwargs) -> XProfile:
        index = self.model_cls.INDEX_TEMPLATE.format(
            entity_id=entity_id,
            profile_admin_api_id=self.model_cls.PROFILE_ADMIN_API_ID,
        )
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
        instance._entity_id = entity_id
        return instance

    def filter(
        self,
        entity_id: str,
        *,
        query: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
        check_at_least: int | None = None,
    ) -> SearchResults:
        index = self.model_cls.INDEX_TEMPLATE.format(
            entity_id=entity_id,
            profile_admin_api_id=self.model_cls.PROFILE_ADMIN_API_ID,
        )
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
            instance._entity_id = entity_id
            instances.append(instance)
        return SearchResults(
            results=instances,
            total_count=response.count,
            matches_estimated=response.total,
            aggregations=getattr(response, 'aggregations', None),
        )

    def get(self, entity_id: str, id: str, *, volatile: bool = False) -> XProfile:
        index = self.model_cls.INDEX_TEMPLATE.format(
            entity_id=entity_id,
            profile_admin_api_id=self.model_cls.PROFILE_ADMIN_API_ID,
        )
        data = client.get(index, id=id, volatile=volatile)
        instance = self.model_cls(data)
        instance._entity_id = entity_id
        return instance


class XProfile:
    PROFILE_ADMIN_API_ID = PROFILES_ADMIN_API
    SCHEMA_ID = PROFILE_SCHEMA
    INDEX_TEMPLATE = "/{entity_id}/{profile_admin_api_id}"
    SCHEMA = {
        '_foreign': f".schema/{PROFILE_SCHEMA}",
        **get_profile_schema(),
    }

    objects = Manager()

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

    def save(self) -> None:
        index = self.INDEX_TEMPLATE.format(
            entity_id=self._entity_id,
            profile_admin_api_id=self.PROFILE_ADMIN_API_ID,
        )
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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"
