"""Categories module for MagnitSearch.

Handles category selection, slug generation, and prompts for both
search categories and local database categories.
"""

import re

from config import DEFAULT_CATEGORIES
from models import Category, ProductCategory


def slugify_category_title(title: str, category_id: int) -> str:
    """Convert a category title to a URL-friendly slug.

    Lowercases the title, replaces 'ё' with 'е', and replaces
    non-alphanumeric characters with hyphens. Falls back to a default
    slug if the result is empty.

    Args:
        title: The category title to slugify.
        category_id: Category ID used as fallback if slug is empty.

    Returns:
        URL-friendly slug string.
    """
    normalized = title.lower().replace("ё", "е")
    slug = re.sub(r"[^a-z0-9а-я]+", "-", normalized, flags=re.IGNORECASE)
    slug = slug.strip("-")
    if not slug:
        slug = f"category-{category_id}"
    return slug


def get_default_categories() -> list[dict]:
    """Get the list of default categories from config.

    Returns a list of category dictionaries with 'id', 'title', and
    pre-computed 'slug' fields.

    Returns:
        List of default category dictionaries.
    """
    return [
        {
            "id": category["id"],
            "title": category["title"],
            "slug": slugify_category_title(category["title"], category["id"]),
        }
        for category in DEFAULT_CATEGORIES
    ]


def get_search_categories() -> list[dict]:
    """Get all available categories for search (default + local DB).

    Combines default categories from config with categories stored
    in the local database, deduplicating by category ID.

    Returns:
        Sorted list of category dictionaries by title.
    """
    categories_by_id: dict[int, dict] = {
        category["id"]: category for category in get_default_categories()
    }

    for category in list(Category.select().order_by(Category.title.asc())):
        categories_by_id[category.id] = {
            "id": category.id,
            "title": category.title,
            "slug": category.slug,
        }

    return sorted(categories_by_id.values(), key=lambda category: category["title"])


def prompt_search_category() -> dict:
    """Prompt the user to select a category for search import.

    Displays a list of available categories and allows the user to
    select one or enter a category ID manually.

    Returns:
        Dictionary with 'id', 'title', and 'slug' of the selected category.

    Raises:
        ValueError: If the selected category index is invalid.
    """
    categories = get_search_categories()
    print("Select category for import:")
    for index, category in enumerate(categories, start=1):
        print(f"{index} - {category['title']} ({category['id']})")
    print("0 - enter category manually")

    selected = input("Category: ").strip()
    if selected == "0":
        category_id = int(input("Enter category id: ").strip())
        title = input("Enter category title: ").strip() or f"Category {category_id}"
        return {
            "id": category_id,
            "title": title,
            "slug": slugify_category_title(title, category_id),
        }

    category_index = int(selected) - 1
    if category_index < 0 or category_index >= len(categories):
        raise ValueError("Unknown category selection")
    return categories[category_index]


def get_local_categories() -> list[Category]:
    """Get all categories that have products in the local database.

    Returns a list of Category model instances that are linked to
    at least one product, sorted by title.

    Returns:
        List of Category instances.
    """
    return list(
        Category.select()
        .join(ProductCategory)
        .group_by(Category.id)
        .order_by(Category.title.asc())
    )


def prompt_local_category() -> Category:
    """Prompt the user to select a category from the local database.

    Displays a list of categories that have products in the database
    and returns the user's selection.

    Returns:
        Selected Category model instance.

    Raises:
        ValueError: If no categories exist or selection is invalid.
    """
    categories = get_local_categories()
    if not categories:
        raise ValueError("No categories found in local database")

    print("Select category from local db:")
    for index, category in enumerate(categories, start=1):
        print(f"{index} - {category.title} ({category.id})")

    selected = int(input("Category: ").strip()) - 1
    if selected < 0 or selected >= len(categories):
        raise ValueError("Unknown category selection")
    return categories[selected]
