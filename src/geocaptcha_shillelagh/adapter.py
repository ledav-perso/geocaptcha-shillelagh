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
_logger.setLevel(logging.DEBUG)

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
    def parse_uri(uri: str) -> tuple[str]:
        _logger.info('gc / parse_uri')
        _logger.debug(f'uri: {uri}')
        matched = _P.match(uri)
        if matched is not None:
            collection = matched.groups()[0]
            _logger.debug(f'collection found: {collection}')
            return (collection,)
        else:
            _logger.error('error parsing uri, no collection identified')
            return (_GC_SESSION,)

    def __init__(self, collection: str, base_url: str, app_id: str, api_key: str):
        _logger.info('gc / __init__')
        super().__init__()

        self.collection = collection
        self.base_url = base_url
        self.app_id = app_id
        self.api_key = api_key

    def get_data(  # pylint: disable=too-many-locals
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterator[Row]:
        _logger.info('gc / get_data')
        conn = _get_headers(kwargs)
        yeld({id: 1, info: "réussite"})
