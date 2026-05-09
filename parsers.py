"""Parsers module for MagnitSearch.

Contains functions for extracting and parsing product data including
weight, price, ingredients, and nutrition facts from API responses.
"""

import json


def find_detail_by_name(details: list[dict], detail_name: str) -> dict | None:
    """Find a detail dictionary by its name in a list of details.

    Searches through a list of detail dictionaries and returns the first one
    that matches the specified name.

    Args:
        details: List of detail dictionaries, each containing a 'name' key.
        detail_name: The name to search for.

    Returns:
        The matching detail dictionary, or None if not found.
    """
    for detail in details:
        if detail.get("name") == detail_name:
            return detail
    return None


def find_parameter_value(parameters: list[dict], parameter_name: str) -> str | None:
    """Find a parameter value by its name in a list of parameters.

    Searches through a list of parameter dictionaries and returns the value
    of the first parameter that matches the specified name.

    Args:
        parameters: List of parameter dictionaries, each containing 'name' and 'value' keys.
        parameter_name: The name of the parameter to find.

    Returns:
        The parameter value as a string, or None if not found.
    """
    for parameter in parameters:
        if parameter.get("name") == parameter_name:
            return parameter.get("value")
    return None


def parse_weight_grams_from_kg(value: str | None) -> int | None:
    """Convert a weight value in kilograms to grams.

    Takes a string representation of a weight in kilograms (e.g., "1.5", "0,750")
    and converts it to an integer value in grams. Handles both comma and dot
    as decimal separators.

    Args:
        value: Weight string in kilograms, or None.

    Returns:
        Weight in grams as an integer, or None if conversion fails or input is invalid.
    """
    if not value:
        return None

    normalized_value = value.replace(",", ".").strip()
    try:
        return int(round(float(normalized_value) * 1000))
    except ValueError:
        return None


def extract_weight_grams(item: dict, details: list[dict]) -> int | None:
    """Extract the weight in grams from a product item.

    Determines the product weight by checking if it's a weighted item first,
    then falling back to parsing the 'Вес, кг' or 'Объем, л' parameters
    from the product details.

    Args:
        item: Product item dictionary containing 'weighted' information.
        details: List of detail dictionaries containing product characteristics.

    Returns:
        Weight in grams as an integer, or None if weight cannot be determined.
    """
    weighted = item.get("weighted") or {}
    if weighted.get("isWeighted"):
        shelf_weight = weighted.get("shelfWeight")
        return shelf_weight if isinstance(shelf_weight, int) else None

    characteristics = find_detail_by_name(details, "Характеристики") or {}
    parameters = characteristics.get("parameters") or []
    weight_value = find_parameter_value(parameters, "Вес, кг")
    if weight_value is None:
        weight_value = find_parameter_value(parameters, "Объем, л")
    return parse_weight_grams_from_kg(weight_value)


def extract_price_per_kg(item: dict, weight_grams: int | None) -> int | None:
    """Calculate the price per kilogram for a product.

    For weighted items, uses the unitPrice directly. For regular items,
    calculates price per kg by dividing the price by weight in kg.

    Args:
        item: Product item dictionary containing 'weighted' and 'price' information.
        weight_grams: The product weight in grams.

    Returns:
        Price per kilogram as an integer, or None if calculation is not possible.
    """
    weighted = item.get("weighted") or {}
    if weighted.get("isWeighted"):
        unit_price = weighted.get("unitPrice")
        return unit_price if isinstance(unit_price, int) else None

    price = item.get("price")
    if not isinstance(price, int) or not weight_grams:
        return None

    return int(round(price * 1000 / weight_grams))


def extract_final_price(item: dict) -> bool:
    """Check if a product has the 'Финальная цена' (Final Price) badge.

    Examines the product's badges list to determine if it has the final
    price badge, which indicates the price cannot be discounted further.

    Args:
        item: Product item dictionary containing 'badges' information.

    Returns:
        True if the product has the final price badge, False otherwise.
    """
    badges = item.get("badges") or []
    return any(badge.get("text") == "Финальная цена" for badge in badges)


def extract_nutrition_facts_type(details: list[dict]) -> str | None:
    """Extract nutrition facts as a JSON string from product details.

    Searches for a detail with type 'nutritionFactsType' and serializes
    it to a JSON string for storage in the database.

    Args:
        details: List of detail dictionaries containing product information.

    Returns:
        JSON string representation of nutrition facts, or None if not found.
    """
    nutrition_facts = next(
        (detail for detail in details if detail.get("type") == "nutritionFactsType"),
        None,
    )
    if not nutrition_facts:
        return None

    return json.dumps(nutrition_facts, ensure_ascii=False)


def extract_ingredients(details: list[dict]) -> str | None:
    """Extract the ingredients list from product details.

    Looks for a detail named 'Состав' (Composition) and returns its value
    as a string.

    Args:
        details: List of detail dictionaries containing product information.

    Returns:
        Ingredients string, or None if not found or not a string.
    """
    ingredients_detail = find_detail_by_name(details, "Состав")
    if not ingredients_detail:
        return None

    value = ingredients_detail.get("value")
    return value if isinstance(value, str) else None
