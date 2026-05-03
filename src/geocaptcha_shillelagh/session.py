"""
GeocaptchaSessionAdapter
---------------
read-only Shillelagh adapter that uses Geocaptcha API admin to collect sessions collections

URI : geocaptcha://session

required parameters :
- base_url : API Endpoint (eg https://geocaptcha.ign.fr/api/v1/admin)
- app_id : admin user name
- api_key : admin api key

optional parameters :
- loglevel : [DEBUG | INFO | WARNING | ERROR | CRITICAL], default to ERROR
"""

import logging
import re

from collections.abc import Iterator
from typing import Any, Optional

import requests

from shillelagh.adapters.base import Adapter
from shillelagh.exceptions import ProgrammingError
from shillelagh.fields import Field, DateTime, Integer, String, Boolean
from shillelagh.typing import RequestedOrder, Row
from shillelagh.filters import Filter

_logger = logging.getLogger("Geocaptcha / sessions")
_logger.setLevel(logging.ERROR)

_GC_PREFIX = "geocaptcha://"

_P = re.compile("^geocaptcha://(session|cuser|kingpin)$")

_GC_SESSION = {
    "collection": "session",
    "fields": {
        # flatten captcha dict
        # "captcha_type": String(),  # "kingpin",
        # "captcha_name": String(),  # "25757-88000",
        # "captcha_angle": Integer(),  # 250,
        "_id": String(),  # "6998b38e66f0bb9f02ac4535",
        "ip": String(),  # "::ffff: 127.0.0.1",
        "success": Boolean(),  # false,
        "attempts": Integer(),  # 1,
        "available": Boolean(),  # false,
        "begin": DateTime(),  # "2026-02-20T19: 18: 38.622Z",
        "end": DateTime(),  # null,
        "referer": String(),  # "application-client-13e274287b298d1191008af11625c30513ddd01d.eu",
        "visited": Boolean(),  # true,
        "response_angle": Integer(),  # 0,
        "response_h": String(),  # "",
        "createdAt": DateTime(),  # "2026-02-20T19: 18: 38.641Z",
        "updatedAt": DateTime(),  # "2026-02-20T19: 18: 48.075Z"
    },
    "path": "sessions",
}

# ---------------------------
# Adapter
# ---------------------------


class GeocaptchaSessionAdapter(Adapter):
    """Shillelagh Adapter customized for Geocaptcha"""

    supports_requested_columns = True
    safe = True

    @staticmethod
    def supports(uri: str, fast: bool, **kwargs: Any) -> bool:
        """is url managed by this Adapter ?"""
        _logger.info("def supports")
        _logger.debug("uri: %s", uri)

        if fast:
            return uri.startswith(_GC_PREFIX)

        return parse_uri(uri) is not None

    @staticmethod
    def parse_uri(uri: str) -> tuple[Optional[str]]:
        """extract collection from uri"""
        _logger.info("def parse_uri")
        _logger.debug("uri: %s", uri)
        matched = _P.match(uri)
        if matched is not None:
            collection = matched.groups()[0]
            _logger.debug("collection found: %s", collection)
            return collection

        _logger.error("error parsing uri, no collection identified")
        return None

    def __init__(self, collection: str, base_url: str, app_id: str, api_key: str):
        _logger.info("def GeocaptchaAdapter __init__")
        super().__init__()

        match collection:
            case "session":
                self.path = _GC_SESSION["path"]
                self.fields = _GC_SESSION["fields"]
            case _:
                _logger.error("collection unavailable: %s", collection)
                self.path = None
                self.fields = None

        self.base_url = base_url
        self.app_id = app_id
        self.api_key = api_key

    def get_columns(self) -> dict[str, Field]:
        """columns return for current collection"""
        _logger.info("def get_columns")
        if self.fields is None:
            return {}

        return self.fields

    def get_data(
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        requested_columns: Optional[set[str]] = None,
        **kwargs: Any,
    ) -> Iterator[Row]:
        """return rows requested"""
        _logger.info("def get_data")
        _logger.debug(
            "bounds: %s, requested_columns: %s, kwargs: %s",
            bounds,
            requested_columns,
            kwargs,
        )
        headers = {"x-app-id": self.app_id, "x-api-key": self.api_key}
        response = requests.get(f"{self.base_url}/{self.collection}", params=headers)
        payload = response.json()
        if not response.ok:
            raise ProgrammingError(f'Error: {payload["error"]["message"]}')

        outline = {}
        for i, row in enumerate(jsonpath.findall(self.path, payload)):
            outline["rowid"] = i
            for key in self.fields.keys():
                outline[key] = row[key] | None

            yield outline
