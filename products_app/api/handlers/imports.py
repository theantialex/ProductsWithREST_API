import asyncpg
from marshmallow import ValidationError
from .base import BaseView
from products_app.utils.pg import MAX_QUERY_ARGS
from products_app.db.schema import items_table
from products_app.api.schema import ImportSchema

from http import HTTPStatus

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from aiomisc import chunk_list
import logging

log = logging.getLogger(__name__)


class ImportsView(BaseView):
    URL = '/imports'

    MAX_ITEMS_PER_INSERT = MAX_QUERY_ARGS // len(items_table.columns)

    @classmethod
    def rename_item_fields(cls, items_dict, date):
        items = {}
        for key, item in items_dict.items():
            item['price_amount'] = 0
            if item['price']:
                item['price_amount'] = 1
            items[key] = {
                'item_id': item['id'],
                'name': item['name'],
                'date': date,
                'type': item['type'],
                'parent_id': item['parentId'],
                'price_sum': item['price'],
                'price_amount': item['price_amount']
            }
        return items
    
    async def validate_types(self, items):
        imported_items = {}
        for item in items:
            query = items_table.select().where(items_table.c.item_id == item['id']).order_by(items_table.c.date.desc())
            db_item = await self.pg.fetchrow(self.get_sql(query))

            if db_item and db_item['type'] != item['type']:
                raise ValidationError('Validation Failed')
            
            if db_item:
                item['ex_parent_id'] = db_item['parent_id']
                item['ex_price_sum'] = db_item['price_sum']
                item['ex_price_amount'] = db_item['price_amount']

            if item['parentId']:
                parent_query = items_table.select().where(items_table.c.item_id == item['parentId']).order_by(items_table.c.date.desc())
                parent = await self.pg.fetchrow(self.get_sql(parent_query))
                
                if (not parent or parent['type'] != 'CATEGORY') and \
                    (item['parentId'] not in imported_items or imported_items[item['parentId']]['type'] != 'CATEGORY'):
                    raise ValidationError('Validation Failed')

            if item['id'] in imported_items:
                raise ValidationError('Validation Failed')

            imported_items[item['id']] = item
        
        return imported_items

    async def get_ancestors(self, id):
        query = """ WITH RECURSIVE parents AS (
                            (SELECT item_id, name, date, type, price_sum, price_amount, parent_id
                                FROM items
                                WHERE item_id = $1::varchar ORDER BY date DESC LIMIT 1)
                            UNION
                            (SELECT op.item_id, op.name, op.date, op.type, op.price_sum, op.price_amount, op.parent_id
                                FROM items op
                                JOIN parents p ON op.item_id = p.parent_id))
                        SELECT DISTINCT ON (parents.item_id) parents.item_id, parents.name, parents.date, parents.type,
                                parents.price_sum, parents.price_amount, parents.parent_id
                        FROM parents
                        ORDER BY parents.item_id, parents.date DESC;
                """

        rows = await self.pg.fetch(query, id)
        return rows
    
    @classmethod
    def calculate_categories_price(self, items):
        for value in items.values():
            if value['parent_id'] and value['price_sum'] and value['parent_id'] in items:
                parent_id = value['parent_id']

                while parent_id != None and parent_id in items:
                    if not items[parent_id]['price_sum']:
                        items[parent_id]['price_sum'] = 0

                    items[parent_id]['price_sum'] += value['price_sum']
                    items[parent_id]['price_amount'] += 1
                    
                    parent_id = items[parent_id]['parent_id']

            if 'ex_parent_id' in value and value['ex_parent_id'] and value['price_sum'] and value['ex_parent_id'] in items:
                parent_id = value['ex_parent_id']

                while parent_id != None and parent_id in items:
                    if not items[parent_id]['price_sum']:
                        items[parent_id]['price_sum'] = 0

                    items[parent_id]['price_sum'] -= value['ex_price_sum']
                    items[parent_id]['price_amount'] -= 1
                    
                    parent_id = items[parent_id]['parent_id']
        return items
    
    async def get_ancestor_updates(self, items, date):
        ancestors = {}
        for key, value in items.items():
            if value['type'] == 'CATEGORY' and 'ex_parent_id' in value:
                ex_price = value['ex_price_sum'] if value['ex_price_sum'] else 0
    
                if not value['price_sum']:
                    value['price_sum'] = ex_price
                else:
                    value['price_sum'] += ex_price
                    value['price_amount'] += value['ex_price_amount']

            keys = {}
            if value['parent_id'] and value['parent_id'] not in items:
                if 'ex_parent_id' in value and value['price_sum'] and value['parent_id'] == value['ex_parent_id']:
                    ex_price = value['ex_price_sum'] if value['ex_price_sum'] else 0
                    price = value['price_sum'] - ex_price
                    amount = value['price_amount'] - value['ex_price_amount']
                else:
                    price = value['price_sum']
                    amount = value['price_amount']
                keys[value['parent_id']] = [price, amount]

            if 'ex_parent_id' in value and (not value['parent_id'] or value['parent_id'] != value['ex_parent_id']):
                price = - value['ex_price_sum'] if value['ex_price_sum'] else 0
                amount = - value['ex_price_amount']
                keys[value['ex_parent_id']] = [price, amount]

            for key, value in keys.items():
                parents = await self.get_ancestors(key)
                if not parents:
                    raise ValidationError('Validation Failed')
                        
                for parent in parents:
                    parent = dict(parent)
                    if parent['item_id'] not in ancestors:
                        parent['price_sum'] = parent['price_sum'] if parent['price_sum'] else 0
                        parent['date'] = date
                        ancestors[parent['item_id']] = parent

                    ancestors[parent['item_id']]['price_sum'] += value[0]
                    ancestors[parent['item_id']]['price_amount'] += value[1]

            
        return items, ancestors



    @docs(summary='Добавить выгрузку с информацией о товарах/категориях')
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.acquire() as conn:
            async with conn.transaction():

                items = self.request['data']['items']
                date = self.request['data']['updateDate']

                items_dict = await self.validate_types(items)
                items_dict = self.rename_item_fields(items_dict, date)
                items_dict = self.calculate_categories_price(items_dict)
                items_dict, ancestors_dict = await self.get_ancestor_updates(items_dict, date)
    
                chunked_insert_rows = chunk_list(ancestors_dict.values(), self.MAX_ITEMS_PER_INSERT)
                for chunk in chunked_insert_rows:
                    query = items_table.insert().values(chunk)
                    await conn.execute(self.get_sql(query))

                chunked_insert_rows = chunk_list(items_dict.values(), self.MAX_ITEMS_PER_INSERT)
                for chunk in chunked_insert_rows:
                    query = items_table.insert().values(chunk)
                    await conn.execute(self.get_sql(query))

                return Response(status=HTTPStatus.OK)


