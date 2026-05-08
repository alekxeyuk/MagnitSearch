from peewee import (
    BooleanField,
    CompositeKey,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from config import DB_PATH, CATEGORIES_TABLE, PRODUCTS_TABLE, PRODUCT_CATEGORIES_TABLE

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    id = TextField(primary_key=True)
    product_id = TextField(null=True)
    name = TextField(null=True)
    price = IntegerField(null=True)
    quantity = IntegerField(null=True)
    image_url = TextField(null=True)
    rating = FloatField(null=True)
    comments_count = IntegerField(null=True)
    discount_percent = IntegerField(null=True)
    old_price = IntegerField(null=True)
    is_promotion = BooleanField(null=True)
    seo_code = TextField(null=True)
    cashback = IntegerField(null=True)
    final_price = BooleanField(null=True)
    nutrition_facts_type = TextField(null=True)
    ingredients = TextField(null=True)
    weight = IntegerField(null=True)
    weight_per_kg = IntegerField(null=True)

    class Meta:
        table_name = PRODUCTS_TABLE


class Category(BaseModel):
    id = IntegerField(primary_key=True)
    title = TextField()
    slug = TextField(unique=True)

    class Meta:
        table_name = CATEGORIES_TABLE


class ProductCategory(BaseModel):
    product = ForeignKeyField(Product, backref='category_links', on_delete='CASCADE')
    category = ForeignKeyField(Category, backref='product_links', on_delete='CASCADE')

    class Meta:
        table_name = PRODUCT_CATEGORIES_TABLE
        primary_key = CompositeKey('product', 'category')


def ensure_product_columns() -> None:
    existing_columns = {
        column_info.name
        for column_info in db.get_columns(Product._meta.table_name)
    }
    expected_columns = {
        'final_price': 'INTEGER',
        'nutrition_facts_type': 'TEXT',
        'ingredients': 'TEXT',
        'weight': 'INTEGER',
        'weight_per_kg': 'INTEGER',
    }

    for column_name, column_type in expected_columns.items():
        if column_name not in existing_columns:
            db.execute_sql(
                f'ALTER TABLE {Product._meta.table_name} ADD COLUMN {column_name} {column_type}'
            )


def ensure_schema() -> None:
    db.create_tables([Product, Category, ProductCategory], safe=True)
    ensure_product_columns()


def upsert_category(category_id: int, title: str, slug: str) -> Category:
    Category.insert(
        id=category_id,
        title=title,
        slug=slug,
    ).on_conflict(
        conflict_target=[Category.id],
        update={
            Category.title: title,
            Category.slug: slug,
        },
    ).execute()
    return Category.get_by_id(category_id)


def link_product_to_category(product_id: str, category_id: int) -> None:
    ProductCategory.insert(
        product=product_id,
        category=category_id,
    ).on_conflict_ignore().execute()
