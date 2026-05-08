import json
import sys

import requests

from categories import prompt_local_category, prompt_search_category
from models import (
    Product,
    ProductCategory,
    db,
    ensure_schema,
    link_product_to_category,
    upsert_category,
)

headers = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    'x-device-id': 'e3267ea9-8f6b-4e17-bca0-64a06ba225c7',
}

item_request_params = {
    'storetype': 'express',
    'catalogtype': '2',
}

base_search_payload = {
    'categories': [],
    'includeAdultGoods': True,
    'pagination': {
        'limit': 32,
        'offset': 0,
    },
    'sort': {
        'order': 'desc',
        'type': 'price',
    },
    'storeCode': '543354',
    'storeType': 'express',
    'catalogType': '2',
}


def build_search_payload(category_id: int) -> dict:
    payload = json.loads(json.dumps(base_search_payload))
    payload['categories'] = [category_id]
    return payload


def find_detail_by_name(details: list[dict], detail_name: str) -> dict | None:
    for detail in details:
        if detail.get('name') == detail_name:
            return detail
    return None


def find_parameter_value(parameters: list[dict], parameter_name: str) -> str | None:
    for parameter in parameters:
        if parameter.get('name') == parameter_name:
            return parameter.get('value')
    return None


def parse_weight_grams_from_kg(value: str | None) -> int | None:
    if not value:
        return None

    normalized_value = value.replace(',', '.').strip()
    try:
        return int(round(float(normalized_value) * 1000))
    except ValueError:
        return None


def extract_weight_grams(item: dict, details: list[dict]) -> int | None:
    weighted = item.get('weighted') or {}
    if weighted.get('isWeighted'):
        shelf_weight = weighted.get('shelfWeight')
        return shelf_weight if isinstance(shelf_weight, int) else None

    characteristics = find_detail_by_name(details, 'Характеристики') or {}
    parameters = characteristics.get('parameters') or []
    weight_value = find_parameter_value(parameters, 'Вес, кг')
    if weight_value is None:
        weight_value = find_parameter_value(parameters, 'Объем, л')
    return parse_weight_grams_from_kg(weight_value)


def extract_weight_per_kg(item: dict, weight_grams: int | None) -> int | None:
    weighted = item.get('weighted') or {}
    if weighted.get('isWeighted'):
        unit_price = weighted.get('unitPrice')
        return unit_price if isinstance(unit_price, int) else None

    price = item.get('price')
    if not isinstance(price, int) or not weight_grams:
        return None

    return int(round(price * 1000 / weight_grams))


def extract_final_price(item: dict) -> bool:
    badges = item.get('badges') or []
    return any(badge.get('text') == 'Финальная цена' for badge in badges)


def extract_nutrition_facts_type(details: list[dict]) -> str | None:
    nutrition_facts = next(
        (detail for detail in details if detail.get('type') == 'nutritionFactsType'),
        None,
    )
    if not nutrition_facts:
        return None

    return json.dumps(nutrition_facts, ensure_ascii=False)


def extract_ingredients(details: list[dict]) -> str | None:
    ingredients_detail = find_detail_by_name(details, 'Состав')
    if not ingredients_detail:
        return None

    value = ingredients_detail.get('value')
    return value if isinstance(value, str) else None


def save_item(item: dict, category_id: int | None = None) -> None:
    image_url = None
    gallery = item.get('gallery')
    if gallery and len(gallery) > 0:
        image_url = gallery[0].get('url')

    ratings = item.get('ratings') or {}
    promotion = item.get('promotion') or {}
    details = item.get('details') or []
    weight = extract_weight_grams(item, details)

    Product.replace(
        id=item.get('id'),
        product_id=item.get('productId'),
        name=item.get('name'),
        price=item.get('price'),
        quantity=item.get('quantity'),
        image_url=image_url,
        rating=ratings.get('rating'),
        comments_count=ratings.get('commentsCount'),
        discount_percent=promotion.get('discountPercent'),
        old_price=promotion.get('oldPrice'),
        is_promotion=promotion.get('isPromotion'),
        seo_code=item.get('seoCode'),
        cashback=item.get('cashback'),
        final_price=extract_final_price(item),
        nutrition_facts_type=extract_nutrition_facts_type(details),
        ingredients=extract_ingredients(details),
        weight=weight,
        weight_per_kg=extract_weight_per_kg(item, weight),
    ).execute()

    if category_id is not None:
        link_product_to_category(item.get('id'), category_id)


def fetch_all_items(category_id: int) -> list[dict]:
    search_payload = build_search_payload(category_id)
    all_items: list[dict] = []
    offset = search_payload['pagination']['offset']
    limit = search_payload['pagination']['limit']
    total_count = None

    while True:
        search_payload['pagination']['offset'] = offset
        response = requests.post(
            'https://magnit.ru/webgate/v2/goods/search',
            headers=headers,
            json=search_payload,
            timeout=30,
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
    response = requests.get(
        f'https://magnit.ru/webgate/v2/goods/{item_id}/stores/{store_id}',
        params=item_request_params,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Item request failed for {item_id} with status {response.status_code}"
        )

    return response.json()


def run_search_mode() -> None:
    category = prompt_search_category()
    upsert_category(category['id'], category['title'], category['slug'])

    items = fetch_all_items(category['id'])
    if not items:
        print('No items returned from search')
        return

    with db.atomic():
        for item in items:
            save_item(item, category_id=category['id'])

    print(f"Saved {len(items)} items to database for {category['title']}")


def run_details_mode() -> None:
    category = prompt_local_category()
    product_ids = (
        Product.select(Product.id)
        .join(ProductCategory)
        .where(ProductCategory.category == category)
    )
    products = list(Product.select().where(Product.id.in_(product_ids)))
    if not products:
        print('No items found in selected category')
        return

    updated_count = 0
    total_count = len(products)
    store_id = str(base_search_payload['storeCode'])
    with db.atomic():
        for index, product in enumerate(products, start=1):
            item = fetch_item_details(product.id, store_id)
            save_item(item, category_id=category.id)
            updated_count += 1
            progress = updated_count / total_count
            bar_length = 30
            filled_length = int(bar_length * progress)
            bar = '#' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(
                f'\r[{bar}] {index}/{total_count} ({progress * 100:.1f}%)'
            )
            sys.stdout.flush()

    print()
    print(f"Updated {updated_count} items from item details for {category.title}")


def get_operation_mode() -> str:
    print('Select operation mode:')
    print('1 - parse data using /search')
    print('2 - request item details for every item stored in db category')
    print('3 - generate category html files from local db')
    print('4 - upload output folder to s3 object storage')
    return input('Mode: ').strip()


def main() -> None:
    try:
        db.connect()
        ensure_schema()

        mode = get_operation_mode()
        if mode == '1':
            run_search_mode()
        elif mode == '2':
            run_details_mode()
        elif mode == '3':
            from generate_index import run_html_mode

            run_html_mode()
        elif mode == '4':
            from s3_upload import run_upload_mode

            run_upload_mode()
        else:
            print('Unknown mode')
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        print(exc)
    finally:
        if not db.is_closed():
            db.close()


if __name__ == '__main__':
    main()
