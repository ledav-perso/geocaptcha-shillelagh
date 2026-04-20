import logging
import urllib.parse
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Union, cast

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


class GeocaptchaAPI(Adapter):
    safe = True

    # Since the adapter doesn't return exact data (see the time columns below)
    # implementing limit/offset is not worth the trouble.
    supports_limit = False
    supports_offset = False

    time = DateTime(filters=[Range], order=Order.ASCENDING, exact=False)

    @staticmethod
    def supports(uri: str, fast: bool = True, **kwargs: Any) -> Optional[bool]:
        print("gc / supports")
        return uri.startswith(_GC_PREFIX)

    @staticmethod
    def parse_uri(uri: str) -> str:
        return uri

    def __init__(self, base_url: str, app_id: str, api_key: str):
        super().__init__()

        self.base_url = base_url
        self.app_id = app_id
        self.api_key = api_key

    def get_data(  # pylint: disable=too-many-locals
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        **kwargs: Any,
    ) -> Iterator[Row]:

        while start <= end:
            url = "https://api.weatherapi.com/v1/history.json"
            params = {"key": self.api_key, "q": self.location, "dt": start}

            query_string = urllib.parse.urlencode(params)
            _logger.info("GET %s?%s", url, query_string)

            response = self._session.get(url, params=params)
            if response.ok:
                payload = response.json()
                local_timezone = dateutil.tz.gettz(
                    payload["location"]["tz_id"])
                for record in payload["forecast"]["forecastday"][0]["hour"]:
                    row = {column: record[column]
                           for column in self.get_columns()}
                    row["time"] = dateutil.parser.parse(record["time"]).replace(
                        tzinfo=local_timezone,
                    )
                    row["rowid"] = int(row["time_epoch"])
                    _logger.debug(row)
                    yield row

            start += timedelta(days=1)
