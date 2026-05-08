"""Pydantic schemas for MagnitSearch API responses.

Validates API responses before saving to database to catch
API contract changes early.

Usage:
    from schemas import Item

    # Validate API response
    validated_item = Item.model_validate(item_data)
    item_dict = validated_item.model_dump(by_alias=True)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GalleryItem(BaseModel):
    """Single gallery image in product data."""

    model_config = ConfigDict(extra="ignore")

    url: str | None = None


class Rating(BaseModel):
    """Product rating information."""

    model_config = ConfigDict(extra="ignore")

    rating: float | None = None
    comments_count: int | None = Field(None, alias="commentsCount")


class Promotion(BaseModel):
    """Product promotion/discount information."""

    model_config = ConfigDict(extra="ignore")

    discount_percent: int | None = Field(None, alias="discountPercent")
    old_price: int | None = Field(None, alias="oldPrice")
    is_promotion: bool | None = Field(None, alias="isPromotion")


class Parameter(BaseModel):
    """Product parameter in characteristics."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    value: str | None = None


class Detail(BaseModel):
    """Product detail section."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    type: str | None = None
    parameters: list[Parameter] | None = None
    value: str | None = None


class Weighted(BaseModel):
    """Weighted product information."""

    model_config = ConfigDict(extra="ignore")

    is_weighted: bool | None = Field(None, alias="isWeighted")
    shelf_weight: int | None = Field(None, alias="shelfWeight")
    unit_price: int | None = Field(None, alias="unitPrice")


class Badge(BaseModel):
    """Product badge (e.g., "Финальная цена")."""

    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class Item(BaseModel):
    """Product item from Magnit API.

    Used for validating both search results and item details responses.
    """

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    product_id: str | None = Field(None, alias="productId")
    name: str | None = None
    price: int | None = None
    quantity: int | None = None
    seo_code: str | None = Field(None, alias="seoCode")
    cashback: int | None = None
    gallery: list[GalleryItem] | None = None
    ratings: Rating | None = None
    promotion: Promotion | None = None
    details: list[Detail] | None = None
    weighted: Weighted | None = None
    badges: list[Badge] | None = None


class Pagination(BaseModel):
    """Pagination information in search response."""

    model_config = ConfigDict(extra="ignore")

    total_count: int | None = Field(None, alias="totalCount")
    has_more: bool | None = Field(None, alias="hasMore")


class SearchResponse(BaseModel):
    """Response from the search API endpoint."""

    model_config = ConfigDict(extra="ignore")

    items: list[dict] | None = None
    pagination: Pagination | None = None
