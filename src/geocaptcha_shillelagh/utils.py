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
