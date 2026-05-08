from peewee import BooleanField, FloatField, IntegerField, Model, SqliteDatabase, TextField

db = SqliteDatabase('products.db')


class Product(Model):
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
        database = db
        table_name = 'products'


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
