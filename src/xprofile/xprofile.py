from __future__ import annotations

from .base import BaseXapianModel
from .schemas import PROFILES_ADMIN_API, PROFILE_SCHEMA, get_profile_schema


class XProfile(BaseXapianModel):
    INDEX_TEMPLATE = f"/{{entity_id}}/{PROFILES_ADMIN_API}"
    SCHEMA_ID = PROFILE_SCHEMA
    SCHEMA = {
        '_foreign': f".schema/{PROFILE_SCHEMA}",
        **get_profile_schema(),
    }
