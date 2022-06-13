from enum import Enum, unique

from sqlalchemy import (
    Column, Date, Enum as PgEnum, ForeignKey, Integer,
    MetaData, String, Table,
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
    offer = 'offer'
    category = 'category'


items_table = Table(
    'items',
    metadata,
    Column('item_id', String, primary_key=True),
    Column('name', String, nullable=False),
    Column('date', Date, nullable=False),
    Column('type', PgEnum(ItemType, name='item_type'), nullable=False),
    Column('price_sum', Integer, nullable=True),
    Column('price_amount', Integer, nullable=True),
    Column('parent_id', String, ForeignKey('items.item_id', ondelete='CASCADE'), index=True, nullable=True)
)

stats_table = Table(
    'statistics',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('item_id', String, ForeignKey('items.item_id', ondelete='CASCADE'), index=True),
    Column('name', String, nullable=False),
    Column('date', Date, nullable=False),
    Column('type', PgEnum(ItemType, name='item_type'), nullable=False),
    Column('price_sum', Integer, nullable=True),
    Column('price_amount', Integer, nullable=True),
    Column('parent_id', String, index=True, nullable=True)
)

