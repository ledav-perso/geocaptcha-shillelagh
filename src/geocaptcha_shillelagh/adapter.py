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
- page_size : Integer, default to 10000
"""

import logging
import re

from collections.abc import Iterator
from typing import Any, Optional

import requests

from shillelagh.adapters.base import Adapter
from shillelagh.exceptions import ProgrammingError
from shillelagh.fields import Field, ISODateTime, Integer, String, Boolean
from shillelagh.typing import RequestedOrder, Row
from shillelagh.filters import Filter, Equal, Range, NotEqual, IsNull, IsNotNull
from shillelagh.fields import Order

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

# API Admin endpoint
_GC_ADMIN_API = "https://geocaptcha.ign.fr/api/v1/admin"

# URI attendue
_GC_PROTOCOL = "geocaptcha://"
_GC_URI_PATTERN = re.compile("^geocaptcha://(session|cuser|kingpin)$")

# collection sessions de l'API admin
_GC_COLLECTION = "session"

_GC_PATH = "sessions"

# liste des champs à renvoyer au driver shillelagh
_GC_FIELDS = {
    "captcha_type": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "kingpin",
    "captcha_challenge_name": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "25757-88000",
    "captcha_challenge_angle": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # 250,
    "ip": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "::ffff: 127.0.0.1",
    "success": Boolean(
        filters=[Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=True,
    ),  # false,
    "attempts": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # 1,
    "begin": ISODateTime(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "2026-02-20T19:18:38.622Z",
    "end": ISODateTime(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # null,
    "referer": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "application-client-13e274287b298d1191008af11625c30513ddd01d.eu",
    "visited": Boolean(
        filters=[Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=True,
    ),  # true,
    "response_angle": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # 0,
    "response_h": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.ANY,
        exact=True,
    ),  # "",
}

# nested fields
# _ to separate branches and leaf
_GC_NESTED_FIELDS = [
    "response_angle",
    "response_h",
    "captcha_type",
    "captcha_challenge_name",
    "captcha_challenge_angle",
]

# default pagination size
_GC_PAGE_SIZE = 1000


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
        _logger.debug("fast: %s", fast)
        # _logger.Debug("kwargs: %s", kwargs)

        # tests URI
        if uri.startswith(_GC_PROTOCOL):
            _logger.debug("uri=%s supported", uri)
            return True

        _logger.debug("uri=%s not supported", uri)
        return False

    @staticmethod
    def parse_uri(uri: str) -> tuple[Optional[str]]:
        """extract collection from uri"""
        _logger.info("def parse_uri")
        _logger.debug("uri: %s", uri)

        matched = _GC_URI_PATTERN.match(uri)

        if matched.group(1) == _GC_COLLECTION:
            _logger.debug("return %s", _GC_COLLECTION)
            return (_GC_COLLECTION,)

        _logger.error("error parsing uri, no collection identified")
        return (None,)

    def __init__(
        self,
        # *args,
        # **kwargs,
        collection: str,
        app_id: str = None,
        api_key: str = None,
        base_url: str = _GC_ADMIN_API,
        log_level: str = "ERROR",
        page_size: int = _GC_PAGE_SIZE,
    ):
        _logger.info("def GeocaptchaAdapter.__init__")

        super().__init__()

        self.collection = collection
        _logger.debug("collection = %s", self.collection)
        if app_id is not None:
            self.app_id = app_id
        else:
            raise ProgrammingError("Error: no app_id in engine parameters (kwargs)")

        if api_key is not None:
            self.api_key = api_key
        else:
            raise ProgrammingError("Error: no api_key in engine parameters (kwargs)")

        self.base_url = base_url

        if log_level in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ]:
            _logger.setLevel(log_level)

        self.page_size = page_size

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
        """
        returns data requested

        data ordered with newerFirst
        no pagination
        no cache
        """
        _logger.info("def get_rows")
        _logger.debug(
            "bounds: %s, requested_columns: %s, kwargs: %s",
            bounds,
            requested_columns,
            kwargs,
        )

        url = f"{self.base_url}/{self.collection}"
        # TODO : redact sensitive data
        headers = {"x-app-id": self.app_id, "x-api-key": self.api_key}
        timeout = 3
        _logger.debug("request : %s, headers: %s", url, headers)
        response = requests.get(
            url,
            params={"nbObjects": self.page_size, "order": "newerFirst"},
            headers=headers,
            timeout=timeout,
        )
        payload = response.json()
        _logger.debug("payload: %s", payload)
        if not response.ok:
            raise ProgrammingError(f"Error: HTTP {response.status_code} / {payload}")

        _logger.debug(
            "sessions: %d returned on %d available",
            payload["nbObjects"],
            payload["nbTotalObjects"],
        )

        output = {}
        for i, objs in enumerate(payload[_GC_PATH]):
            _logger.debug("# %d, %s", i, objs)
            output["rowid"] = i

            # nested fields
            for value in _GC_NESTED_FIELDS:
                _logger.debug("recherche de %s", value)
                chain = value.split(sep="_")
                current_objs = objs
                branches = chain[:-1]
                leaf = chain[-1]
                _logger.debug("branches: %s, leaf: %s", branches, leaf)
                for key in branches:
                    _logger.debug("recherche %s", key)
                    if key in current_objs:
                        current_objs = current_objs[key]
                    else:
                        raise ProgrammingError(
                            f"Error: branch {key} of {value} unavailable in API response : {objs}",
                        )

                _logger.debug("recherche de %s", leaf)
                if leaf in current_objs:
                    objs[value] = current_objs[leaf]
                else:
                    raise ProgrammingError(
                        f"Error: field {leaf} of {value} unavailable in API response : {objs}",
                    )

            for key, value in _GC_FIELDS.items():
                _logger.debug("traitement de %s, %s", key, value)
                if key in objs:
                    if objs[key] is not None:
                        output[key] = objs[key]
                else:
                    raise ProgrammingError(
                        f"Error: no field {key} available in API response : {objs}",
                    )

            _logger.debug("output: %s", output)
            yield output
