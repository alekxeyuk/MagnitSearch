"""API module for MagnitSearch.

Handles HTTP requests to the Magnit API including search queries
and item details retrieval.
"""

import json

import requests

from config import (
    CATALOG_TYPE,
    HEADERS,
    ITEM_DETAILS_ENDPOINT,
    ITEM_REQUEST_PARAMS,
    REQUEST_TIMEOUT,
    SEARCH_ENDPOINT,
    SEARCH_INCLUDE_ADULT_GOODS,
    SEARCH_PAGINATION_LIMIT,
    SEARCH_PAGINATION_OFFSET,
    SEARCH_SORT_ORDER,
    SEARCH_SORT_TYPE,
    STORE_CODE,
    STORE_TYPE,
)

base_search_payload = {
    'categories': [],
    'includeAdultGoods': SEARCH_INCLUDE_ADULT_GOODS,
    'pagination': {
        'limit': SEARCH_PAGINATION_LIMIT,
        'offset': SEARCH_PAGINATION_OFFSET,
    },
    'sort': {
        'order': SEARCH_SORT_ORDER,
        'type': SEARCH_SORT_TYPE,
    },
    'storeCode': STORE_CODE,
    'storeType': STORE_TYPE,
    'catalogType': CATALOG_TYPE,
}


def build_search_payload(category_id: int) -> dict:
    """Build search payload for the Magnit API search endpoint.

    Creates a deep copy of the base search payload and sets the categories
    list to contain only the specified category ID.

    Args:
        category_id: The numeric category ID to search for.

    Returns:
        A dictionary containing the complete search payload ready for POST request.
    """
    payload = json.loads(json.dumps(base_search_payload))
    payload['categories'] = [category_id]
    return payload


def fetch_all_items(category_id: int) -> list[dict]:
    """Fetch all items from a category using paginated API requests.

    Iterates through all pages of search results until all items are retrieved
    or no more pages are available. Handles pagination automatically based on
    totalCount and hasMore flags from the API response.

    Args:
        category_id: The numeric category ID to fetch items from.

    Returns:
        A list of item dictionaries from the search results.

    Raises:
        RuntimeError: If the search request fails (non-200 status code).
    """
    search_payload = build_search_payload(category_id)
    all_items: list[dict] = []
    offset = search_payload['pagination']['offset']
    limit = search_payload['pagination']['limit']
    total_count = None

    while True:
        search_payload['pagination']['offset'] = offset
        response = requests.post(
            SEARCH_ENDPOINT,
            headers=HEADERS,
            json=search_payload,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Search request failed with status {response.status_code}")

        response_json: dict = response.json()
        items = response_json.get('items')
        pagination = response_json.get('pagination') or {}

        if not isinstance(items, list) or not items:
            break

        all_items.extend(items)

        total_count = pagination.get('totalCount', total_count)
        has_more = pagination.get('hasMore', False)
        offset += limit

        if total_count is not None and len(all_items) >= total_count:
            break
        if not has_more:
            break

    return all_items


def fetch_item_details(item_id: str, store_id: str) -> dict:
    """Fetch detailed information for a specific product item.

    Retrieves complete product details including ingredients, nutrition facts,
    and other detailed information from the Magnit API item details endpoint.

    Args:
        item_id: The unique identifier of the product item.
        store_id: The store code to fetch details for.

    Returns:
        A dictionary containing the full item details from the API.

    Raises:
        RuntimeError: If the item request fails (non-200 status code).
    """
    response = requests.get(
        ITEM_DETAILS_ENDPOINT.format(item_id=item_id, store_id=store_id),
        params=ITEM_REQUEST_PARAMS,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Item request failed for {item_id} with status {response.status_code}"
        )

    return response.json()
