"""
GeocaptchaSessionAdapter
---------------
read-only Shillelagh adapter that uses Geocaptcha API admin to collect sessions collections

URI : geocaptcha://session

required parameters :
- app_id : admin user name
- api_key : admin api key

optional parameters :
- base_url : API Endpoint, default to "https://geocaptcha.ign.fr/api/v1/admin"
- log_level : "DEBUG" | "INFO" | "WARNING" | "ERROR", default to "ERROR"
"""

import logging

from collections.abc import Iterator
from typing import Any, Optional

import requests
import jsonpath

from shillelagh.adapters.base import Adapter
from shillelagh.exceptions import ProgrammingError
from shillelagh.fields import Field, DateTime, Integer, String, Boolean
from shillelagh.typing import RequestedOrder, Row
from shillelagh.filters import Filter

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

# API Admin endpoint
_GC_ADMIN_API = "https://geocaptcha.ign.fr/api/v1/admin"

# URI attendue
_GC_URI = "geocaptcha://session"

# collection sessions de l'API admin
_GC_COLLECTION = "session"

_GC_PATH = "sessions"

# liste des champs à renvoyer au driver shillelagh
_GC_FIELDS = {
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
}


# ---------------------------
# Adapter
# ---------------------------


class GeocaptchaSessionAdapter(Adapter):
    """Shillelagh Adapter customized for Geocaptcha sessions collection"""

    supports_requested_columns = True
    safe = True

    @staticmethod
    def supports(uri: str, fast: bool = True, **kwargs: Any) -> Optional[bool]:
        """is url managed by this Adapter ?"""
        _logger.info("def supports")
        _logger.debug("uri: %s", uri)

        # URI inconnue
        if uri != _GC_URI:
            return False

        # pré-validation basée sur l'URI seulement
        if fast:
            # check de l'URI seulement
            return True

        # TODO : test de connexion à implémenter
        # - récupérer les informations de connexion dans kwargs
        # - faire un test de connexion pour récupérer quelques éléments de la collection
        # - comparer les fields obtenus avec les fields prévus (_GC_FIELDS)
        return True

    @staticmethod
    def parse_uri(uri: str) -> tuple[Optional[str]]:
        """extract collection from uri"""
        _logger.info("def parse_uri")
        _logger.debug("uri: %s", uri)

        if uri == _GC_URI:
            return _GC_COLLECTION

        _logger.error("error parsing uri, no collection identified")
        return None

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        _logger.info("def GeocaptchaAdapter __init__")
        _logger.debug(
            "args: %s, kwargs: %s",
            args,
            kwargs,
        )

        super().__init__()

        self.collection = args[0]
        if "app_id" in kwargs:
            self.app_id = kwargs.app_id

        if "api_key" in kwargs:
            self.api_key = kwargs.api_key

        if "base_url" in kwargs:
            self.base_url = kwargs.base_url
        else:
            self.base_url = _GC_ADMIN_API

        if "log_level" in kwargs:
            log_level = kwargs.log_level
            if log_level in [
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
            ]:
                _logger.setLevel(kwargs.log_level)

    def get_columns(self) -> dict[str, Field]:
        """columns return for current collection"""
        _logger.info("def get_columns")

        return _GC_FIELDS

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
        response = requests.get(
            f"{self.base_url}/{self.collection}", params=headers, timeout=3
        )
        payload = response.json()
        if not response.ok:
            raise ProgrammingError(f'Error: {payload["error"]["message"]}')

        outline = {}
        for i, row in enumerate(jsonpath.findall(_GC_PATH, payload)):
            outline["rowid"] = i
            for key in _GC_FIELDS:
                outline[key] = row[key] | None

            yield outline
