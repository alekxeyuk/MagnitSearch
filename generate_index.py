import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import (
    MECHANICAL_DEBONING_PATTERN,
    OUTPUT_DIR,
    TEMPLATES_DIR,
    PRICE_DIVISOR,
    PRODUCT_PAGE_URL,
    WEIGHT_KG_THRESHOLD,
    DISCOUNT_MIN_PERCENT,
    DISCOUNT_MAX_PERCENT,
)
from models import Category, Product, ProductCategory, db

MECHANICAL_DEBONING_REGEX = re.compile(MECHANICAL_DEBONING_PATTERN, re.IGNORECASE)

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    keep_trailing_newline=True,
)


def format_price(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value / PRICE_DIVISOR:.2f} ₽"


def format_weight(weight: int | None) -> str | None:
    if weight is None:
        return None
    if weight >= WEIGHT_KG_THRESHOLD and weight % WEIGHT_KG_THRESHOLD == 0:
        return f"{weight // WEIGHT_KG_THRESHOLD} кг"
    if weight >= WEIGHT_KG_THRESHOLD:
        return f"{weight / WEIGHT_KG_THRESHOLD:.2f} кг"
    return f"{weight} г"


def has_mechanical_deboning(ingredients: str | None) -> bool:
    if not ingredients:
        return False
    normalized = ingredients.replace('-', ' ')
    return bool(MECHANICAL_DEBONING_REGEX.search(normalized))


def apply_discount(value: int | None, discount_percent: float, can_discount: bool) -> int | None:
    if value is None or not can_discount or discount_percent <= 0:
        return value
    discounted_value = value * (100 - discount_percent) / 100
    return int(round(discounted_value))


def parse_discount_percent(raw_value: str) -> float:
    normalized = raw_value.strip().replace(',', '.')
    if not normalized:
        return 0.0

    discount_percent = float(normalized)
    if discount_percent < DISCOUNT_MIN_PERCENT or discount_percent > DISCOUNT_MAX_PERCENT:
        raise ValueError('Discount percent must be between 0 and 100')
    return discount_percent


def ask_discount_percent() -> float:
    print('Do you have a promocode discount?')
    raw_value = input('Enter discount percent, or 0 if none: ')
    return parse_discount_percent(raw_value)


def build_item_view(product: Product, discount_percent: float) -> dict:
    can_discount = not bool(product.final_price)
    effective_price = apply_discount(product.price, discount_percent, can_discount)
    effective_weight_per_kg = apply_discount(product.weight_per_kg, discount_percent, can_discount)

    return {
        'name': product.name or 'Без названия',
        'image_url': product.image_url,
        'price_rub': format_price(effective_price),
        'old_price_rub': (
            format_price(product.price)
            if can_discount and discount_percent > 0 and effective_price != product.price
            else format_price(product.old_price)
        ),
        'weight_per_kg_rub': format_price(effective_weight_per_kg) or 'Нет данных',
        'weight_label': format_weight(product.weight),
        'final_price': bool(product.final_price),
        'ingredients': product.ingredients,
        'promo_applied': can_discount and discount_percent > 0,
        'effective_weight_per_kg': effective_weight_per_kg if effective_weight_per_kg is not None else 10**12,
        'page_url': (
            PRODUCT_PAGE_URL.format(product_id=product.id)
            if product.id else None
        ),
    }


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def get_category_products(category: Category, discount_percent: float) -> list[dict]:
    query = (
        Product.select()
        .join(ProductCategory)
        .where(ProductCategory.category == category)
    )
    items = [
        build_item_view(product, discount_percent)
        for product in query
        if not has_mechanical_deboning(product.ingredients)
    ]
    return sorted(items, key=lambda item: (item['effective_weight_per_kg'], item['name']))


def generate_category_pages(discount_percent: float) -> list[dict]:
    output_dir = ensure_output_dir()
    categories = (
        Category.select()
        .join(ProductCategory)
        .group_by(Category.id)
        .order_by(Category.title.asc())
    )

    generated_categories: list[dict] = []
    category_template = jinja_env.get_template('category.j2')
    for category in categories:
        items = get_category_products(category, discount_percent)
        if not items:
            continue

        filename = f'{category.slug}.html'
        rendered_html = category_template.render(
            category=category,
            items=items,
            discount_percent=discount_percent,
        )
        (output_dir / filename).write_text(rendered_html, encoding='utf-8')
        generated_categories.append(
            {
                'title': category.title,
                'filename': filename,
                'item_count': len(items),
            }
        )

    return generated_categories


def generate_categories_index(categories: list[dict], discount_percent: float) -> Path:
    output_dir = ensure_output_dir()
    index_template = jinja_env.get_template('index.j2')
    rendered_html = index_template.render(
        categories=categories,
        discount_percent=discount_percent,
    )
    output_file = output_dir / 'index.html'
    output_file.write_text(rendered_html, encoding='utf-8')
    return output_file


def run_html_mode() -> None:
    if db.is_closed():
        db.connect()

    discount_percent = ask_discount_percent()
    generated_categories = generate_category_pages(discount_percent)
    output_file = generate_categories_index(generated_categories, discount_percent)
    print(f"Generated {output_file}")
