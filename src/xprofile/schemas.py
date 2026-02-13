"""
Dubalu Framework: graph Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2019,2020,2021,2022,2023,2024 Dubalu International LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import annotations

from typing import Any

from xapiand import constants as xconst

PROFILES_ADMIN_API = "Profile Admin API"
PROFILE_SCHEMA = "Profile Schema"

PROFILE_LIST_ADMIN_API = "Profile List Admin API"
PROFILE_LIST_SCHEMA = "Profile List Schema"

PERSONAL_TYPE = 'personal'
BUSINESS_TYPE = 'business'
RESELLER_TYPE = 'reseller'
REFERRAL_TYPE = 'referral'
SUPPLIER_TYPE = 'supplier'
MASHUP_TYPE = 'mashup'
AFFINITY_TYPE = 'affinity'
DSSUPPLIER_TYPE = 'dssupplier'

CAN_MANAGE_PROFILE = 'can_manage_profile'


def get_profile_schema() -> dict[str, dict[str, Any]]:
    return {
        'id': {
            '_type': 'uuid',
            '_required': False,
            '_src': '_id',
            '_label': "Object Id",
            '_help_text': "Object Id (UUID)",
        },
        'visibility': {
            '_type': 'array/term',
            '_required': False,
            '_write_only': True,
            '_label': "Visibility",
            '_help_text': "Visibility is used to give access to the object",
        },
        'created_at': {
            '_type': 'date',
            '_required': False,
            '_null': True,
            '_label': "Created at",
            '_accuracy': xconst.DAY_TO_YEAR_ACCURACY,
            '_help_text': "Date the object was first created",
        },
        'updated_at': {
            '_type': 'date',
            '_required': False,
            '_null': True,
            '_label': "Updated at",
            '_accuracy': xconst.DAY_TO_YEAR_ACCURACY,
            '_help_text': "Date the object was last updated",
        },
        'deleted_at': {
            '_type': 'date',
            '_required': False,
            '_null': True,
            '_label': "Deleted at",
            '_accuracy': xconst.DAY_TO_YEAR_ACCURACY,
            '_help_text': "Date the object was flagged as deleted",
        },
        'is_deleted': {
            '_type': 'boolean',
            '_required': False,
            '_default': False,
            '_write_only': True,
            '_label': "Is deleted",
            '_help_text': "Flags the object as deleted",
        },
        "name": {
            "_type": "string",
            "_index": "terms",
            "_help_text": "User name",
        },
        "mashup": {
            "_type": "uuid",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_help_text": "Mashup ID the user registered through",
        },
        "is_active": {
            "_type": "boolean",
            "_index": "field_terms",
            "_default": False,
            "_help_text": "Indicates wheter or not the user has been activated",
        },
        "is_guest": {
            "_type": "boolean",
            "_index": "field_terms",
            "_default": False,
            "_help_text": "Indicates wheter or not the user is guest",
        },
        "guest_prefix": {
            "_type": "term",
            "_index": "none",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Used to encode URLs capable log in guest users "
                "without password"),
        },
        "public_guest_key": {
            "_type": "term",
            "_index": "none",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Used to encode URLs capable log in guest users "
                "without password"),
        },
        "slug": {
            "_type": "string",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_help_text": "Slug of the user's store",
        },
        "store_id": {
            "_type": "uuid",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_help_text": "ID of the store the user registered through",
        },
        "affinity_node": {  # TODO: to be deprecated
            "_type": "uuid",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": "ID of the affinity node the user registered through",
        },
        "affinity_group": {  # TODO: to be deprecated
            "_type": "json",
            "_index": "none",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Denormalised affinity group for commission "
                "dispersions related to the users's resells"),
        },
        "subscriptions": {
            "_type": "json",
            "_index": "none",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Denormalised subscription information"),
        },
        "referral": {
            "_type": "uuid",
            "_index": "terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Referral the user registered through. This may be "
                "the owner of an affinity store, for example. This will not be "
                "used for commission dispersion, but to keep track of the "
                "registrations/purchases promoted by a user"),
        },
        "campaign": {
            "_type": "term",
            "_index": "terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Referral's campaign the user registered through. "
                "This may be the owner of an affinity store, for example. This "
                "will not be used for commission dispersion, but to keep track "
                "of the registrations/purchases promoted by a user"),
        },
        "click_id": {
            "_type": "term",
            "_index": "terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Click ID of the referral's campaign the user "
                "registered through. This may be the owner of an affinity "
                "store, for example. This will not be used for commission "
                "dispersion, but to keep track of the registrations/purchases "
                "promoted by a user"),
        },
        "bio": {
            "_type": "text",
            "_index": "terms",
            "_required": False,
            "_null": True,
            "_help_text": ("Public bio of the user"),
        },
        "description": {
            "_type": "text",
            "_index": "terms",
            "_required": False,
            "_help_text": ("Public description of the user"),
        },
        "main_type": {
            "_type": "term",
            "_index": "field_terms",
            "_choices": (PERSONAL_TYPE, BUSINESS_TYPE, RESELLER_TYPE,
                REFERRAL_TYPE, AFFINITY_TYPE, DSSUPPLIER_TYPE,
                SUPPLIER_TYPE, MASHUP_TYPE),
            "_required": False,
            "_help_text": ("Public main 'role' of the user"),
        },
        "is_proxy": {
            "_type": "boolean",
            "_index": "field_all",
            "_required": False,
            "_default": False,
        },
        "root_affinity_store_owner": {
            "_type": "uuid",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
        },
        # PRIVATE contact info
        "username_email": {
            "_type": "term",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Email username"),
        },
        "username_phone": {
            "_type": "term",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Phone username"),
        },
        "contact_email": {
            "_type": "term",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Private contact email"),
        },
        "is_contact_email_active": {
            "_type": "boolean",
            "_index": "field_all",
            "_required": False,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Indicates whether or not the contact email has been "
                "validated by PIN"),
        },
        "contact_phone": {
            "_type": "term",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Private contact phone"),
        },
        "contact_country_code": {
            "_type": "term",
            "_index": "field_terms",
            "_required": False,
            "_null": True,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Private country code of contact phone"),
        },
        "is_contact_phone_active": {
            "_type": "boolean",
            "_index": "field_all",
            "_required": False,
            "_write_only": {
                "get": [CAN_MANAGE_PROFILE],
            },
            "_help_text": ("Indicates whether or not the contac phone has been "
                "validated by PIN"),
        },
        "images": {
            "_type": "json",
            "_index": "none",
            "_required": False,
            "_help_text": ("Denormalised user's profile images"),
        },
        "heartbeat": {
            "_type": "date",
            "_index": "none",
            "_required": False,
            "_null": True,
        },
    }
