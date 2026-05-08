"""Config module for MagnitSearch.

Contains all configuration constants including API endpoints,
database settings, and file paths for the application.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

BASE_URL = "https://magnit.ru/webgate/v2"

SEARCH_ENDPOINT = f"{BASE_URL}/goods/search"
ITEM_DETAILS_ENDPOINT = f"{BASE_URL}/goods/{{item_id}}/stores/{{store_id}}"
PRODUCT_PAGE_URL = "https://magnit.ru/product/{product_id}"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-device-id": "e3267ea9-8f6b-4e17-bca0-64a06ba225c7",
}

ITEM_REQUEST_PARAMS = {
    "storetype": "express",
    "catalogtype": "2",
}

STORE_CODE = "543354"
STORE_TYPE = "express"
CATALOG_TYPE = "2"

SEARCH_PAGINATION_LIMIT = 32
SEARCH_PAGINATION_OFFSET = 0
SEARCH_INCLUDE_ADULT_GOODS = True
SEARCH_SORT_ORDER = "desc"
SEARCH_SORT_TYPE = "price"

DEFAULT_CATEGORIES = [
    {"id": 64249, "title": "Колбасы и сосиски"},
]

DB_PATH = "products.db"

PRODUCTS_TABLE = "products"
CATEGORIES_TABLE = "categories"
PRODUCT_CATEGORIES_TABLE = "product_categories"

OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

AWS_CONFIG_PATH = PROJECT_ROOT / ".aws" / "config"
AWS_CREDENTIALS_PATH = PROJECT_ROOT / ".aws" / "credentials"
AWS_PARAMS_PATH = PROJECT_ROOT / ".aws" / "params"

REQUEST_TIMEOUT = 30

PRICE_DIVISOR = 100
WEIGHT_KG_THRESHOLD = 1000
DISCOUNT_MIN_PERCENT = 0
DISCOUNT_MAX_PERCENT = 100

PROGRESS_BAR_LENGTH = 30

MECHANICAL_DEBONING_PATTERN = r"мех\w*\s+обвал\w*"
