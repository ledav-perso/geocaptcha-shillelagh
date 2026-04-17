"""
Shillelagh adapters for the GeoCaptcha REST API (https://github.com/IGNF/GeoCaptchaAPI).

Two adapters are provided:

* **GeoCaptchaSessionAdapter** – exposes the ``/api/v1/admin/session`` endpoint as a
  virtual table of captcha-solving sessions.

* **GeoCaptchaCUserAdapter** – exposes the ``/api/v1/admin/cuser`` endpoint as a
  virtual table of API client users / access keys.

Both adapters match any URL whose path ends with the respective resource path so that
different deployments of the GeoCaptcha API (e.g. staging vs production) are supported
transparently::

    # Sessions table
    SELECT * FROM "https://geocaptcha.example.com/api/v1/admin/session"

    # Users table
    SELECT * FROM "https://geocaptcha.example.com/api/v1/admin/cuser"

Authentication credentials are **never** embedded in the URI.  Pass them as adapter
connection arguments when opening the connection::

    from shillelagh.backends.apsw.db import connect

    conn = connect(
        ":memory:",
        adapter_kwargs={
            "geocaptchasessionadapter": {
                "api_key": "YOUR_API_KEY",
                "app_id":  "YOUR_APP_ID",
            },
            "geocaptchacuseradapter": {
                "api_key": "YOUR_API_KEY",
                "app_id":  "YOUR_APP_ID",
            },
        },
    )

Or, more concisely, when both adapters share credentials you can register them once
via the ``geocaptchaapi`` key (both adapters inspect the same key)::

    conn = connect(
        ":memory:",
        adapter_kwargs={
            "geocaptchasessionadapter": {"api_key": "...", "app_id": "..."},
        },
    )
"""

import logging
import re
import urllib.parse
from collections.abc import Iterator
from datetime import timedelta
from typing import Any, Optional

from shillelagh.adapters.base import Adapter
from shillelagh.fields import Boolean, DateTime, Float, Integer, Order, String
from shillelagh.filters import Equal, Filter, Range
from shillelagh.lib import get_session
from shillelagh.typing import RequestedOrder, Row

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Page size used when paginating API responses.
_PAGE_SIZE = 100

#: Regex that matches the *session* resource path.
_SESSION_PATH_RE = re.compile(r"^.*/api/v\d+/admin/session/?$")

#: Regex that matches the *cuser* resource path.
_CUSER_PATH_RE = re.compile(r"^.*/api/v\d+/admin/cuser/?$")

#: Rough cost model constant (rows × fetch cost per row).
_INITIAL_COST = 0
_FETCH_COST = 1000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_all_pages(
    session: Any,
    base_url: str,
    result_key: str,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    """Fetch all pages of a paginated GeoCaptcha API endpoint.

    The API uses ``firstObject`` (1-based index) and ``nbObjects`` (page size)
    query parameters.

    :param session: A :class:`requests_cache.CachedSession` instance.
    :param base_url: The endpoint URL without pagination parameters.
    :param result_key: The JSON key in the response that contains the list of items.
    :param headers: HTTP headers to send with every request.
    :returns: A flat list of all items fetched across all pages.
    """
    items: list[dict[str, Any]] = []
    first_object = 1

    while True:
        params = {"firstObject": first_object, "nbObjects": _PAGE_SIZE}
        _logger.info("GET %s params=%s", base_url, params)
        response = session.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        page_items: list[dict[str, Any]] = payload.get(result_key) or []
        items.extend(page_items)

        if len(page_items) < _PAGE_SIZE:
            # Last page – no more data to fetch.
            break

        first_object += _PAGE_SIZE

    return items


def _build_auth_headers(api_key: str, app_id: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "x-api-key": api_key,
        "x-app-id": app_id,
    }


# ---------------------------------------------------------------------------
# GeoCaptchaSessionAdapter
# ---------------------------------------------------------------------------


class GeoCaptchaSessionAdapter(Adapter):
    """Shillelagh adapter for the GeoCaptcha ``/api/v1/admin/session`` endpoint.

    Each row represents one captcha-solving *session* recorded by the API.

    Column mapping
    ~~~~~~~~~~~~~~

    =================== ============ ==============================================
    Column              Type         Notes
    =================== ============ ==============================================
    ``session_id``      String       Unique session identifier.
    ``success``         Boolean      ``True`` if the user solved the captcha.
    ``begin``           DateTime     Session start time (ISO-8601 from API).
    ``end``             DateTime     Session end time (ISO-8601 from API).
    ``duration``        Float        ``end - begin`` in seconds (``NULL`` if either
                                     timestamp is absent, unparseable, or the computed
                                     value is negative).
    ``challenge_name``  String       Name of the geographic challenge presented.
    =================== ============ ==============================================
    """

    safe = True

    supports_limit = False
    supports_offset = False

    # ------------------------------------------------------------------
    # Column definitions
    # ------------------------------------------------------------------

    session_id = String(filters=[Equal], order=Order.NONE, exact=True)
    success = Boolean(filters=[Equal], order=Order.NONE, exact=True)
    begin = DateTime(filters=[Range], order=Order.ASCENDING, exact=False)
    end = DateTime(filters=[Range], order=Order.NONE, exact=False)
    duration = Float()
    challenge_name = String(filters=[Equal], order=Order.NONE, exact=True)

    # ------------------------------------------------------------------
    # Adapter protocol
    # ------------------------------------------------------------------

    @staticmethod
    def supports(uri: str, fast: bool = True, **kwargs: Any) -> Optional[bool]:
        """Return ``True`` if *uri* points to a GeoCaptcha session resource."""
        parsed = urllib.parse.urlparse(uri)
        return bool(_SESSION_PATH_RE.match(parsed.path))

    @staticmethod
    def parse_uri(uri: str) -> tuple[str]:
        """Return the base URL (scheme + netloc + path) as the only argument."""
        parsed = urllib.parse.urlparse(uri)
        base_url = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        )
        return (base_url,)

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        app_id: str = "",
    ) -> None:
        super().__init__()
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._app_id = app_id
        self._session = get_session(
            request_headers={},
            cache_name="geocaptcha_session_cache",
            expire_after=timedelta(minutes=3),
        )

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def get_cost(
        self,
        filtered_columns: list[tuple[str, Any]],
        order: list[tuple[str, RequestedOrder]],
    ) -> float:
        return _INITIAL_COST + _FETCH_COST

    def get_data(
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        **kwargs: Any,
    ) -> Iterator[Row]:
        headers = _build_auth_headers(self._api_key, self._app_id)
        raw_sessions = _fetch_all_pages(
            self._session,
            self._base_url,
            "sessions",
            headers,
        )

        for idx, session in enumerate(raw_sessions):
            row = self._parse_session(idx, session)
            _logger.debug("session row: %s", row)
            yield row

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_session(idx: int, session: dict[str, Any]) -> Row:
        """Convert a raw API session dict to a :class:`Row`."""
        begin_raw: Optional[str] = session.get("begin")
        end_raw: Optional[str] = session.get("end")

        # duration in seconds (only meaningful when both timestamps exist)
        duration: Optional[float] = None
        if begin_raw and end_raw:
            try:
                import dateutil.parser as _dp

                begin_dt = _dp.parse(begin_raw)
                end_dt = _dp.parse(end_raw)
                delta = (end_dt - begin_dt).total_seconds()
                if delta >= 0:
                    duration = delta
            except (ValueError, TypeError):
                pass

        challenge_name: Optional[str] = None
        captcha = session.get("captcha") or {}
        challenge = captcha.get("challenge") or {}
        challenge_name = challenge.get("name")

        return {
            "rowid": idx,
            "session_id": session.get("id"),
            "success": session.get("success"),
            "begin": begin_raw,
            "end": end_raw,
            "duration": duration,
            "challenge_name": challenge_name,
        }


# ---------------------------------------------------------------------------
# GeoCaptchaCUserAdapter
# ---------------------------------------------------------------------------


class GeoCaptchaCUserAdapter(Adapter):
    """Shillelagh adapter for the GeoCaptcha ``/api/v1/admin/cuser`` endpoint.

    Each row represents one API client user (*cuser*) – essentially an access-key
    record that grants access to the GeoCaptcha client-facing API.

    Column mapping
    ~~~~~~~~~~~~~~

    =========== ====== ======================================================
    Column      Type   Notes
    =========== ====== ======================================================
    ``app_id``  String Unique application identifier / key name.
    ``email``   String Contact e-mail address for the key holder.
    ``referer`` String HTTP ``Referer`` domain allowed for this key (note: the HTTP
                       standard intentionally uses the misspelling *referer*).
    ``role``    String Role assigned to the key (e.g. ``"user"``, ``"admin"``).
    =========== ====== ======================================================
    """

    safe = True

    supports_limit = False
    supports_offset = False

    # ------------------------------------------------------------------
    # Column definitions
    # ------------------------------------------------------------------

    app_id = String(filters=[Equal], order=Order.NONE, exact=True)
    email = String(filters=[Equal], order=Order.NONE, exact=True)
    referer = String(filters=[Equal], order=Order.NONE, exact=True)
    role = String(filters=[Equal], order=Order.NONE, exact=True)

    # ------------------------------------------------------------------
    # Adapter protocol
    # ------------------------------------------------------------------

    @staticmethod
    def supports(uri: str, fast: bool = True, **kwargs: Any) -> Optional[bool]:
        """Return ``True`` if *uri* points to a GeoCaptcha cuser resource."""
        parsed = urllib.parse.urlparse(uri)
        return bool(_CUSER_PATH_RE.match(parsed.path))

    @staticmethod
    def parse_uri(uri: str) -> tuple[str]:
        """Return the base URL (scheme + netloc + path) as the only argument."""
        parsed = urllib.parse.urlparse(uri)
        base_url = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        )
        return (base_url,)

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        app_id: str = "",
    ) -> None:
        super().__init__()
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._app_id = app_id
        self._session = get_session(
            request_headers={},
            cache_name="geocaptcha_cuser_cache",
            expire_after=timedelta(minutes=3),
        )

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def get_cost(
        self,
        filtered_columns: list[tuple[str, Any]],
        order: list[tuple[str, RequestedOrder]],
    ) -> float:
        return _INITIAL_COST + _FETCH_COST

    def get_data(
        self,
        bounds: dict[str, Filter],
        order: list[tuple[str, RequestedOrder]],
        **kwargs: Any,
    ) -> Iterator[Row]:
        headers = _build_auth_headers(self._api_key, self._app_id)
        raw_cusers = _fetch_all_pages(
            self._session,
            self._base_url,
            "cusers",
            headers,
        )

        for idx, cuser in enumerate(raw_cusers):
            row: Row = {
                "rowid": idx,
                "app_id": cuser.get("appId"),
                "email": cuser.get("email"),
                "referer": cuser.get("referer"),
                "role": cuser.get("role"),
            }
            _logger.debug("cuser row: %s", row)
            yield row
