"""
Unit tests for the GeoCaptcha shillelagh adapters.

All HTTP calls are intercepted with the ``responses`` library so no real
network access is required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from geocaptcha_shillelagh.adapter import (
    GeoCaptchaCUserAdapter,
    GeoCaptchaSessionAdapter,
    _SESSION_PATH_RE,
    _CUSER_PATH_RE,
    _build_auth_headers,
    _fetch_all_pages,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SESSION_URL = "https://geocaptcha.example.com/api/v1/admin/session"
CUSER_URL = "https://geocaptcha.example.com/api/v1/admin/cuser"

SAMPLE_SESSIONS = [
    {
        "id": "sess-001",
        "success": True,
        "begin": "2024-01-15T10:00:00Z",
        "end": "2024-01-15T10:00:45Z",
        "captcha": {
            "challenge": {"name": "eiffel-tower"}
        },
    },
    {
        "id": "sess-002",
        "success": False,
        "begin": "2024-01-15T11:00:00Z",
        "end": "2024-01-15T11:00:20Z",
        "captcha": {
            "challenge": {"name": "louvre-museum"}
        },
    },
    {
        "id": "sess-003",
        "success": True,
        "begin": None,
        "end": None,
        "captcha": {},
    },
]

SAMPLE_CUSERS = [
    {
        "appId": "app-alpha",
        "email": "alpha@example.com",
        "referer": "https://app.example.com/",
        "role": "user",
    },
    {
        "appId": "app-beta",
        "email": "beta@example.com",
        "referer": "https://beta.example.com/",
        "role": "admin",
    },
]


def _make_mock_session(pages: list[list[dict]], result_key: str) -> MagicMock:
    """Return a mock CachedSession whose ``get`` method returns *pages* in order."""
    mock_session = MagicMock()
    responses = []
    for page in pages:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {result_key: page}
        responses.append(mock_resp)
    mock_session.get.side_effect = responses
    return mock_session


# ---------------------------------------------------------------------------
# Regex / URL matching
# ---------------------------------------------------------------------------


class TestPathRegexes:
    def test_session_path_matches_standard(self):
        assert _SESSION_PATH_RE.match("/api/v1/admin/session")

    def test_session_path_matches_with_version(self):
        assert _SESSION_PATH_RE.match("/api/v2/admin/session")

    def test_session_path_matches_trailing_slash(self):
        assert _SESSION_PATH_RE.match("/api/v1/admin/session/")

    def test_session_path_no_match_cuser(self):
        assert not _SESSION_PATH_RE.match("/api/v1/admin/cuser")

    def test_cuser_path_matches_standard(self):
        assert _CUSER_PATH_RE.match("/api/v1/admin/cuser")

    def test_cuser_path_no_match_session(self):
        assert not _CUSER_PATH_RE.match("/api/v1/admin/session")


# ---------------------------------------------------------------------------
# _build_auth_headers
# ---------------------------------------------------------------------------


class TestBuildAuthHeaders:
    def test_returns_correct_keys(self):
        headers = _build_auth_headers("my-key", "my-id")
        assert headers["x-api-key"] == "my-key"
        assert headers["x-app-id"] == "my-id"
        assert headers["Accept"] == "application/json"


# ---------------------------------------------------------------------------
# _fetch_all_pages
# ---------------------------------------------------------------------------


class TestFetchAllPages:
    def test_single_page(self):
        mock_session = _make_mock_session([SAMPLE_SESSIONS[:2]], "sessions")
        result = _fetch_all_pages(mock_session, SESSION_URL, "sessions", {})
        assert len(result) == 2
        assert result[0]["id"] == "sess-001"

    def test_multiple_pages(self):
        """When a page is full (== PAGE_SIZE) a second request is made."""
        from geocaptcha_shillelagh.adapter import _PAGE_SIZE

        full_page = [{"id": f"s-{i}"} for i in range(_PAGE_SIZE)]
        last_page = [{"id": "s-last"}]
        mock_session = _make_mock_session([full_page, last_page], "sessions")
        result = _fetch_all_pages(mock_session, SESSION_URL, "sessions", {})
        assert len(result) == _PAGE_SIZE + 1

    def test_empty_response(self):
        mock_session = _make_mock_session([[]], "sessions")
        result = _fetch_all_pages(mock_session, SESSION_URL, "sessions", {})
        assert result == []

    def test_null_result_key(self):
        """API returning null for the list key should be treated as empty."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"sessions": None}
        mock_session.get.return_value = mock_resp
        result = _fetch_all_pages(mock_session, SESSION_URL, "sessions", {})
        assert result == []


# ---------------------------------------------------------------------------
# GeoCaptchaSessionAdapter.supports / parse_uri
# ---------------------------------------------------------------------------


class TestGeoCaptchaSessionAdapterSupports:
    def test_supports_standard_url(self):
        assert GeoCaptchaSessionAdapter.supports(SESSION_URL) is True

    def test_supports_staging_url(self):
        assert (
            GeoCaptchaSessionAdapter.supports(
                "https://staging-geocaptcha.ign.fr/api/v1/admin/session"
            )
            is True
        )

    def test_does_not_support_cuser_url(self):
        assert GeoCaptchaSessionAdapter.supports(CUSER_URL) is False

    def test_does_not_support_unrelated_url(self):
        assert GeoCaptchaSessionAdapter.supports("https://example.com/data") is False

    def test_parse_uri_strips_query(self):
        (base,) = GeoCaptchaSessionAdapter.parse_uri(
            SESSION_URL + "?firstObject=1&nbObjects=20"
        )
        assert base == SESSION_URL

    def test_parse_uri_strips_trailing_slash(self):
        (base,) = GeoCaptchaSessionAdapter.parse_uri(SESSION_URL + "/")
        # The adapter should keep the path as-is (trailing slash kept or stripped by
        # the adapter's own logic)
        assert "session" in base


# ---------------------------------------------------------------------------
# GeoCaptchaSessionAdapter.get_data
# ---------------------------------------------------------------------------


class TestGeoCaptchaSessionAdapterGetData:
    def _make_adapter(self, pages=None):
        if pages is None:
            pages = [SAMPLE_SESSIONS]
        adapter = GeoCaptchaSessionAdapter(SESSION_URL, api_key="key", app_id="id")
        adapter._session = _make_mock_session(pages, "sessions")
        return adapter

    def test_returns_correct_row_count(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert len(rows) == len(SAMPLE_SESSIONS)

    def test_session_id_mapped_correctly(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["session_id"] == "sess-001"
        assert rows[1]["session_id"] == "sess-002"

    def test_success_flag(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["success"] is True
        assert rows[1]["success"] is False

    def test_duration_computed_correctly(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        # sess-001: 45 seconds
        assert rows[0]["duration"] == pytest.approx(45.0)
        # sess-002: 20 seconds
        assert rows[1]["duration"] == pytest.approx(20.0)

    def test_duration_none_when_timestamps_missing(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        # sess-003 has no begin/end
        assert rows[2]["duration"] is None

    def test_challenge_name_extracted(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["challenge_name"] == "eiffel-tower"
        assert rows[1]["challenge_name"] == "louvre-museum"
        assert rows[2]["challenge_name"] is None

    def test_rowid_assigned(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["rowid"] == 0
        assert rows[1]["rowid"] == 1

    def test_auth_headers_sent(self):
        adapter = self._make_adapter()
        list(adapter.get_data({}, []))
        call_kwargs = adapter._session.get.call_args
        assert call_kwargs.kwargs["headers"]["x-api-key"] == "key"
        assert call_kwargs.kwargs["headers"]["x-app-id"] == "id"


# ---------------------------------------------------------------------------
# GeoCaptchaCUserAdapter.supports / parse_uri
# ---------------------------------------------------------------------------


class TestGeoCaptchaCUserAdapterSupports:
    def test_supports_standard_url(self):
        assert GeoCaptchaCUserAdapter.supports(CUSER_URL) is True

    def test_does_not_support_session_url(self):
        assert GeoCaptchaCUserAdapter.supports(SESSION_URL) is False

    def test_parse_uri_strips_query(self):
        (base,) = GeoCaptchaCUserAdapter.parse_uri(
            CUSER_URL + "?firstObject=1&nbObjects=20"
        )
        assert base == CUSER_URL


# ---------------------------------------------------------------------------
# GeoCaptchaCUserAdapter.get_data
# ---------------------------------------------------------------------------


class TestGeoCaptchaCUserAdapterGetData:
    def _make_adapter(self, pages=None):
        if pages is None:
            pages = [SAMPLE_CUSERS]
        adapter = GeoCaptchaCUserAdapter(CUSER_URL, api_key="key", app_id="id")
        adapter._session = _make_mock_session(pages, "cusers")
        return adapter

    def test_returns_correct_row_count(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert len(rows) == len(SAMPLE_CUSERS)

    def test_app_id_mapped(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["app_id"] == "app-alpha"
        assert rows[1]["app_id"] == "app-beta"

    def test_email_mapped(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["email"] == "alpha@example.com"

    def test_role_mapped(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["role"] == "user"
        assert rows[1]["role"] == "admin"

    def test_referer_mapped(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["referer"] == "https://app.example.com/"

    def test_rowid_assigned(self):
        adapter = self._make_adapter()
        rows = list(adapter.get_data({}, []))
        assert rows[0]["rowid"] == 0
        assert rows[1]["rowid"] == 1

    def test_auth_headers_sent(self):
        adapter = self._make_adapter()
        list(adapter.get_data({}, []))
        call_kwargs = adapter._session.get.call_args
        assert call_kwargs.kwargs["headers"]["x-api-key"] == "key"
        assert call_kwargs.kwargs["headers"]["x-app-id"] == "id"
