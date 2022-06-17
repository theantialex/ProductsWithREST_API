from enum import Enum, unique

from sqlalchemy import (
    Column, DateTime, Enum as PgEnum, Integer,
    MetaData, String, Table
)

convention = {
    'all_column_names': lambda constraint, table: '_'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix__%(table_name)s__%(all_column_names)s',
    'uq': 'uq__%(table_name)s__%(all_column_names)s',
    'ck': 'ck__%(table_name)s__%(constraint_name)s',
    'fk': 'fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s',
    'pk': 'pk__%(table_name)s'
}

metadata = MetaData(naming_convention=convention)

@unique
class ItemType(Enum):
    offer = 'OFFER'
    category = 'CATEGORY'


items_table = Table(
    'items',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('item_id', String, index=True, nullable=False),
    Column('name', String, nullable=False),
    Column('date', DateTime, nullable=False),
    Column('type', PgEnum(ItemType, name='item_type'), nullable=False),
    Column('price_sum', Integer, nullable=True),
    Column('price_amount', Integer, nullable=False),
    Column('parent_id', String, index=True, nullable=True)
)

