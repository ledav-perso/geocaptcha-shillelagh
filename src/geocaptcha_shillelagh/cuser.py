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

#: Regex that matches the *kingpin* resource path.
_KINGPIN_PATH_RE = re.compile(r"^.*/api/v\d+/admin/kingpin/?$")

#: Rough cost model constant (rows × fetch cost per row).
_INITIAL_COST = 0
_FETCH_COST = 1000


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
