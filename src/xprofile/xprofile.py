from __future__ import annotations

from xapiand import client, TransportError

from .schemas import PROFILES_ADMIN_API, PROFILE_SCHEMA, get_profile_schema


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
        return self.model_cls(data)

    def get(self, entity_id: str, id: str) -> XProfile:
        index = self.model_cls.INDEX_TEMPLATE.format(
            entity_id=entity_id,
            profile_admin_api_id=self.model_cls.PROFILE_ADMIN_API_ID,
        )
        data = client.get(index, id=id)
        return self.model_cls(data)


class XProfile:
    PROFILE_ADMIN_API_ID = PROFILES_ADMIN_API
    SCHEMA_ID = PROFILE_SCHEMA
    INDEX_TEMPLATE = "/{entity_id}/{profile_admin_api_id}"
    SCHEMA = {
        '_foreign': f".schema/{PROFILE_SCHEMA}",
        **get_profile_schema(),
    }

    objects = Manager()

    def __init__(self, data: dict) -> None:
        self._data = data

    def __getattr__(self, name: str):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}") from None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"
