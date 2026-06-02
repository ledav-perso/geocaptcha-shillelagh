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

from requests_cache import CachedSession, RedisCache
from valkey import Valkey

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
        order=Order.NONE,
        exact=False,
    ),  # "kingpin",
    "captcha_challenge_name": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # "25757-88000",
    "captcha_challenge_angle": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # 250,
    "ip": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # "::ffff: 127.0.0.1",
    "success": Boolean(
        filters=[Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # false,
    "attempts": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=True,
    ),  # 1,
    "begin": ISODateTime(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # "2026-02-20T19:18:38.622Z",
    "end": ISODateTime(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # null,
    "referer": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # "application-client-13e274287b298d1191008af11625c30513ddd01d.eu",
    "visited": Boolean(
        filters=[Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # true,
    "response_angle": Integer(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
    ),  # 0,
    "response_h": String(
        filters=[Range, Equal, NotEqual, IsNull, IsNotNull],
        order=Order.NONE,
        exact=False,
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

# default max extract sessions
_GC_LIMIT_SIZE = 100000

# cache expiration in seconds
_GC_CACHE_EXPIRATION = 14400

# extract cursor from URL
_GC_URI_CURSOR = re.compile(r"cursor=(\d+)")

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
        limit_size: int = _GC_LIMIT_SIZE,
        cache_expiration: int = _GC_CACHE_EXPIRATION,
        cache_server: str = "locahost",
        cache_port: int = 6379,
        cache_db: int = 15,
        cache_username: str = "geocaptcha",
        cache_password: str = "geocaptcha",
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

        self.limit_size = limit_size

        connection = Valkey(
            host=cache_server,
            port=cache_port,
            db=cache_db,
            password=cache_password,
            username=cache_username,
        )
        backend = RedisCache(connection=connection)
        self._session = CachedSession(
            "geocaptcha",
            backend=backend,
            expire_after=cache_expiration,
            stale_while_revalidate=True,
        )

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
        pagination
        valkey cache
        """
        _logger.info("def get_data")
        _logger.debug(
            "bounds: %s, requested_columns: %s, kwargs: %s",
            bounds,
            requested_columns,
            kwargs,
        )

        cursor = None
        page_number = 0
        num = 0
        while True:
            payload = self._prepare_request(cursor)
            page_number += 1

            if _GC_PATH not in payload:
                _logger.error("response API without sessions: %s", payload)
                break

            sessions = payload[_GC_PATH]

            if len(sessions) == 0:
                _logger.debug("no rows left")
                break

            _logger.debug(
                "page: %d, sessions: %d returned on %d total sessions",
                page_number,
                len(sessions),
                payload["nbTotalObjects"],
            )

            for i, obj in enumerate(sessions):
                if num < self.limit_size:
                    yield self._parse_row(num + i, obj)
                    num += 1
                else:
                    _logger.info(
                        "limit size achieved on collecting sessions: %d", num + 1
                    )
                    break

            if "next" in payload:
                matched = _GC_URI_CURSOR.search(payload["next"])
                if matched is not None:
                    cursor = matched.group(1)
                else:
                    _logger.debug("end of pagination")
                    break
            else:
                _logger.error("no next field in payload: %s", payload)

    def _prepare_request(self, cursor: Optional[str]) -> dict:
        """prepares URL, requests endpoint and returns response"""
        url = f"{self.base_url}/{self.collection}"
        # TODO : redact sensitive data
        headers = {"x-app-id": self.app_id, "x-api-key": self.api_key}
        timeout = 3
        _logger.debug("request : %s, headers: %s", url, headers)
        params = {
            "nbObjects": self.page_size,
            "order": "newerFirst",
            "paginated": "true",
        }
        if cursor is not None:
            params["cursor"] = cursor

        response = self._session.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
        )
        payload = response.json()
        if not response.ok:
            raise ProgrammingError(f"Error: HTTP {response.status_code} / {payload}")

        return payload

    def _parse_row(self, num: int, obj: dict) -> dict:
        """parse Geocaptcha row for shillelagh"""
        output = {}
        # _logger.debug("# %d, %s", i, obj)
        output["rowid"] = num

        # nested fields
        for value in _GC_NESTED_FIELDS:
            # _logger.debug("recherche de %s", value)
            chain = value.split(sep="_")
            current_obj = obj
            branches = chain[:-1]
            leaf = chain[-1]
            for key in branches:
                # _logger.debug("recherche %s", key)
                if key in current_obj:
                    current_obj = current_obj[key]
                else:
                    #    _logger.info(
                    #        "branch %s of %s unavailable in API response : %s",
                    #        key,
                    #        value,
                    #        obj,
                    #    )
                    current_obj = None

            if isinstance(current_obj, dict) and leaf in current_obj:
                obj[value] = current_obj[leaf]
            else:
                #    _logger.info(
                #        "field %s of %s unavailable in API response : %s",
                #        leaf,
                #        value,
                #        objs,
                #    )
                obj[value] = None

        for key, value in _GC_FIELDS.items():
            # _logger.debug("traitement de %s, %s", key, value)
            if key in obj:
                if obj[key] is not None:
                    output[key] = obj[key]
            else:
                raise ProgrammingError(
                    f"Error: no field {key} available in API response : {obj}",
                )

        # _logger.debug("output: %s", output)
        return output
