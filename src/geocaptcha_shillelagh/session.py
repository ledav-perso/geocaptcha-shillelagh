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
_SESSION_PATH_RE = re.compile(r"^Geocaptcha://session?$")

#: Regex that matches the *cuser* resource path.
_CUSER_PATH_RE = re.compile(r"^Geocaptcha://cuser?$")

#: Regex that matches the *kingpin* resource path.
_KINGPIN_PATH_RE = re.compile(r"^Geocaptcha://kingpin?$")

#: Rough cost model constant (rows × fetch cost per row).
_INITIAL_COST = 0
_FETCH_COST = 1000


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
    ``ip`̀               String       IP source
    ``success``         Boolean      ``True`` if the user solved the captcha.
    ``attempt`̀          Integer      number of attempts
    ``begin``           DateTime     Session start time (ISO-8601 from API).
    ``end``             DateTime     Session end time (ISO-8601 from API).
    ``duration``        Float        ``end - begin`` in seconds (``NULL`` if either
                                     timestamp is absent, unparseable, or the computed
                                     value is negative).
    ``referer``         String       HTTP ``Referer`` domain declared by the user.
    ``visited``         Boolean      captha has been attempted by user and validation made by client backend
    ``challenge_name``  String       Name of the geographic challenge presented
    ``challenge_type``  String       captcha type (Kingpin, Quiz)
    `̀ challenge_mismatch`` Float       distance between response and attempted answer
    =================== ============ ==============================================
    """

    safe = True

    supports_limit = False
    supports_offset = False

    # ------------------------------------------------------------------
    # Column definitions
    # ------------------------------------------------------------------

    session_id = String(filters=[Equal], order=Order.NONE, exact=True)
    ip = String(filters=[Equal], order=Order.NONE, exact=True)
    success = Boolean(filters=[Equal], order=Order.NONE, exact=True)
    attempt = Integer()
    begin = DateTime(filters=[Range], order=Order.ASCENDING, exact=False)
    end = DateTime(filters=[Range], order=Order.NONE, exact=False)
    duration = Float()
    referer = String(filters=[Equal], order=Order.NONE, exact=True)
    visited = Boolean(filters=[Equal], order=Order.NONE, exact=True)
    challenge_name = String(filters=[Equal], order=Order.NONE, exact=True)
    challenge_type = String(filters=[Equal], order=Order.NONE, exact=True)
    challenge_mismatch = Float()

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
        challenge_type = challenge.get("type")

        return {
            "rowid": idx,
            "session_id": session.get("id"),
            "ip": session.get("ip"),
            "success": session.get("success"),
            "attempt": session.get("attempt"),
            "begin": begin_raw,
            "end": end_raw,
            "duration": duration,
            "referer": session.get("referer"),
            "visited": session.get("visited"),
            "challenge_name": challenge_name,
            "challenge_type": session.get("challengeType"),
            "challenge_mismatch": 0,
        }
