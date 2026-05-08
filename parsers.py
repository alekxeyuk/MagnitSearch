import json


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
