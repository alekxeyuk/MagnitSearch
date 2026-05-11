"""Main module for MagnitSearch.

Entry point for the application with operation modes for searching,
fetching details, generating HTML, and uploading to S3.
"""

from typing import cast

import requests

from api import base_search_payload, fetch_all_items, fetch_item_details
from categories import (
    get_local_categories,
    prompt_local_category,
    prompt_search_category,
)
from config import PROGRESS_BAR_LENGTH
from generate_index import run_html_mode
from logging_config import setup_logger
from models import (
    Product,
    ProductCategory,
    db,
    ensure_schema,
    link_product_to_category,
    upsert_category,
)
from parsers import (
    extract_final_price,
    extract_ingredients,
    extract_nutrition_facts_type,
    extract_weight_grams,
    extract_price_per_kg,
)
from s3_upload import run_upload_mode

logger = setup_logger(__name__)


def print_progress(current: int, total: int, bar_length: int = 30) -> None:
    """Print a progress bar to stdout.

    Args:
        current: Current progress count.
        total: Total count.
        bar_length: Length of the progress bar in characters.
    """
    progress = current / total
    filled = int(bar_length * progress)
    progress_bar = "#" * filled + "-" * (bar_length - filled)
    print(
        f"\r[{progress_bar}] {current}/{total} ({progress * 100:.1f}%)",
        end="",
        flush=True,
    )


def save_item(item: dict, category_id: int | None = None) -> None:
    """Save or update a product item in the database.

    Extracts relevant product information from the API response and saves
    it to the database using upsert (replace) logic. Also links the product
    to a category if category_id is provided.

    Args:
        item: Product item dictionary from the API response.
        category_id: Optional category ID to link the product to.
    """
    image_url = None
    gallery = item.get("gallery")
    if gallery:
        image_url = gallery[0].get("url")

    product_id = item.get("id")
    ratings = item.get("ratings") or {}
    promotion = item.get("promotion") or {}
    details = item.get("details") or []
    weight = extract_weight_grams(item, details)

    Product.replace(
        id=product_id,
        name=item.get("name"),
        price=item.get("price"),
        quantity=item.get("quantity"),
        image_url=image_url,
        rating=ratings.get("rating"),
        comments_count=ratings.get("commentsCount"),
        discount_percent=promotion.get("discountPercent"),
        old_price=promotion.get("oldPrice"),
        is_promotion=promotion.get("isPromotion"),
        seo_code=item.get("seoCode"),
        cashback=item.get("cashback"),
        final_price=extract_final_price(item),
        nutrition_facts_type=extract_nutrition_facts_type(details),
        ingredients=extract_ingredients(details),
        weight=weight,
        price_per_kg=extract_price_per_kg(item, weight),
    ).execute()

    if category_id is not None and product_id is not None:
        link_product_to_category(product_id, category_id)


def run_search_mode() -> None:
    """Run the search mode to fetch and save products by category.

    Prompts the user to select a search category, then fetches all items
    from that category using the API and saves them to the database.
    """
    category = prompt_search_category()
    upsert_category(category["id"], category["title"], category["slug"])

    items = fetch_all_items(category["id"])
    if not items:
        logger.info("No items returned from search")
        return

    with db.atomic():
        for item in items:
            save_item(item, category_id=category["id"])

    logger.info("Saved %d items to database for %s", len(items), category["title"])


def run_details_mode() -> None:
    """Run the details mode to fetch detailed info for existing products.

    Prompts the user to select a local category, then fetches detailed
    information for each product in that category using the item details
    API and updates the database records.
    """
    category = prompt_local_category()
    products = list(
        Product.select()
        .join(ProductCategory)
        .where(ProductCategory.category == category)
    )
    if not products:
        logger.warning("No items found in selected category")
        return

    updated_count = 0
    total_count = len(products)
    store_id = str(base_search_payload["storeCode"])
    with db.atomic():
        for _, product in enumerate(products, start=1):
            item = fetch_item_details(product.id, store_id)
            save_item(item, category_id=cast(int, category.id))
            updated_count += 1
            print_progress(updated_count, total_count, PROGRESS_BAR_LENGTH)

    print(end="\n")
    logger.info(
        "Updated %d items from item details for %s", updated_count, category.title
    )


def update_item_prices(item: dict, category_id: int) -> None:
    """Update only price-related fields for an existing product.

    Updates price, quantity, rating, discount_percent, old_price,
    is_promotion, cashback, and final_price without touching other fields.
    Also ensures the product-category link exists.

    Args:
        item: Product item dictionary from the API response.
        category_id: Category ID to link the product to.
    """
    product_id = item.get("id")
    if product_id is None:
        return

    ratings = item.get("ratings") or {}
    promotion = item.get("promotion") or {}

    Product.update(
        price=item.get("price"),
        quantity=item.get("quantity"),
        rating=ratings.get("rating"),
        discount_percent=promotion.get("discountPercent"),
        old_price=promotion.get("oldPrice"),
        is_promotion=promotion.get("isPromotion"),
        cashback=item.get("cashback"),
        final_price=extract_final_price(item),
    ).where(Product.id == product_id).execute()

    link_product_to_category(product_id, category_id)


def run_update_all_mode() -> None:
    """Run the update mode: refresh prices for all local DB categories.

    Fetches all items via /search for every category stored in the local
    database and updates only price-related fields without touching
    detailed info previously scraped by mode 2.
    """
    categories = get_local_categories()
    if not categories:
        logger.warning("No categories found in local database")
        return

    for category in categories:
        logger.info("Updating %s (%d)", category.title, category.id)
        upsert_category(category.id, category.title, category.slug)
        items = fetch_all_items(category.id)
        if not items:
            logger.info("No items returned for %s", category.title)
            continue

        with db.atomic():
            for item in items:
                update_item_prices(item, category_id=cast(int, category.id))

        logger.info("Updated %d items for %s", len(items), category.title)


def get_operation_mode() -> str:
    """Prompt the user to select an operation mode.

    Displays available operation modes and returns the user's selection.

    Returns:
        The user's input as a string representing the chosen mode.
    """
    logger.info("Select operation mode:")
    logger.info("0 - update prices for all categories using /search")
    logger.info("1 - parse data using /search")
    logger.info("2 - request item details for every item stored in db category")
    logger.info("3 - generate category html files from local db")
    logger.info("4 - upload output folder to s3 object storage")
    return input("Mode: ").strip()


def main() -> None:
    """Main entry point for the MagnitSearch application.

    Connects to the database, ensures the schema is up-to-date, and
    dispatches to the appropriate operation mode based on user input.
    Handles common exceptions and ensures database connection is closed.
    """
    try:
        db.connect()
        ensure_schema()

        mode = get_operation_mode()
        match mode:
            case "0":
                run_update_all_mode()
            case "1":
                run_search_mode()
            case "2":
                run_details_mode()
            case "3":
                run_html_mode()
            case "4":
                run_upload_mode()
            case _:
                logger.warning("Unknown mode: %s", mode)
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        logger.error(exc)
    finally:
        if not db.is_closed():
            db.close()


if __name__ == "__main__":
    main()
