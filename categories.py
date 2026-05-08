import re

from config import DEFAULT_CATEGORIES
from models import Category, ProductCategory


def slugify_category_title(title: str, category_id: int) -> str:
    normalized = title.lower().replace('ё', 'е')
    slug = re.sub(r'[^a-z0-9а-я]+', '-', normalized, flags=re.IGNORECASE)
    slug = slug.strip('-')
    if not slug:
        slug = f'category-{category_id}'
    return slug


def get_default_categories() -> list[dict]:
    return [
        {
            'id': category['id'],
            'title': category['title'],
            'slug': slugify_category_title(category['title'], category['id']),
        }
        for category in DEFAULT_CATEGORIES
    ]


def get_search_categories() -> list[dict]:
    categories_by_id: dict[int, dict] = {
        category['id']: category
        for category in get_default_categories()
    }

    for category in Category.select().order_by(Category.title.asc()):
        categories_by_id[category.id] = {
            'id': category.id,
            'title': category.title,
            'slug': category.slug,
        }

    return sorted(categories_by_id.values(), key=lambda category: category['title'])


def prompt_search_category() -> dict:
    categories = get_search_categories()
    print('Select category for import:')
    for index, category in enumerate(categories, start=1):
        print(f"{index} - {category['title']} ({category['id']})")
    print('0 - enter category manually')

    selected = input('Category: ').strip()
    if selected == '0':
        category_id = int(input('Enter category id: ').strip())
        title = input('Enter category title: ').strip() or f'Category {category_id}'
        return {
            'id': category_id,
            'title': title,
            'slug': slugify_category_title(title, category_id),
        }

    category_index = int(selected) - 1
    if category_index < 0 or category_index >= len(categories):
        raise ValueError('Unknown category selection')
    return categories[category_index]


def get_local_categories() -> list[Category]:
    return list(
        Category.select()
        .join(ProductCategory)
        .group_by(Category.id)
        .order_by(Category.title.asc())
    )


def prompt_local_category() -> Category:
    categories = get_local_categories()
    if not categories:
        raise ValueError('No categories found in local database')

    print('Select category from local db:')
    for index, category in enumerate(categories, start=1):
        print(f"{index} - {category.title} ({category.id})")

    selected = int(input('Category: ').strip()) - 1
    if selected < 0 or selected >= len(categories):
        raise ValueError('Unknown category selection')
    return categories[selected]
