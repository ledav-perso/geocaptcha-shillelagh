import logging
import urllib.parse
import re
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Union, cast
from dataclasses import dataclass

import dateutil.parser
import dateutil.tz

from shillelagh.adapters.base import Adapter
from shillelagh.exceptions import ImpossibleFilterError
from shillelagh.fields import DateTime, Float, IntBoolean, Integer, Order, String
from shillelagh.filters import Filter, Impossible, Operator, Range
from shillelagh.lib import get_session
from shillelagh.typing import RequestedOrder, Row

_logger = logging.getLogger(__name__)

_GC_PREFIX = "geocaptcha://"
_GC_SESSION = "session"
_GC_CUSER = "cuser"
_GC_KINGPIN = "kingpin"
_P = re.compile('^geocaptcha://(session|cuser|kingpin)$')


@dataclass
class Connexion:
    base_url: str
    app_id: str
    api_key: str


class GeocaptchaAdapter(Adapter):
    safe = True

    @staticmethod
    def supports(uri: str, fast: bool, **kwargs: Any) -> bool:
        _logger.info('gc / supports')
        _logger.debug(f'uri: {uri}')
        return uri.startswith(_GC_PREFIX)

    @staticmethod
    def parse_uri(uri: str) -> Tuple[Optional[str]]:
        _logger.info('gc / parse_uri')
        table = _P.match(uri)
        if table is not None:
            return table.groups()[0]
        else:
            return None

    def __init__(self):
        _logger.info('gc / __init__')
        super().__init__()

    def get_data(  # pylint: disable=too-many-locals
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        **kwargs: Any,
    ) -> Iterator[Row]:
        _logger.info('gc / get_data')
        conn = _get_headers(kwargs)
        yeld({id: 1, info: "réussite"})

    @staticmethod
    def _get_headers(**kwargs: Any) -> Connexion:
        logger.info('gc / _get_headers')
        request_headers = kwargs.get("request_headers", {})
        base_url = request_headers.base_url | None
        app_id = request_headers.app_id | None
        api_key = request_headers.api_key | None

        return Connexion(base_url, app_id, api_key)
