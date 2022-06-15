from marshmallow import ValidationError
from .base import BaseView
from products_app.utils.pg import MAX_QUERY_ARGS
from products_app.db.schema import items_table, stats_table
from products_app.api.schema import ImportSchema

from http import HTTPStatus
from typing import Generator

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from aiomisc import chunk_list
from sqlalchemy import select, bindparam
from sqlalchemy.sql import text



class ImportsView(BaseView):
    URL = '/imports'

    MAX_ITEMS_PER_INSERT = MAX_QUERY_ARGS // len(items_table.columns)

    @classmethod
    def make_items_rows(cls, items, date) -> Generator:
        """
        Генерирует данные готовые для вставки в таблицу items.
        """
        for item in items:
            item['price_amount'] = 0
            if item['price']:
                item['price_amount'] = 1
            yield {
                'item_id': item['id'],
                'name': item['name'],
                'date': date,
                'type': item['type'],
                'parent_id': item['parentId'],
                'price_sum': item['price'],
                'price_amount': item['price_amount']
            }
    
    @classmethod
    async def divide_insert_update_items(cls, items):
        insert_items = []
        update_items = []
        update_parents = {}
        for item in items:
            query = items_table.select('parent_id', 'type').where(items_table.c.item_id == item['id'])
            db_item = await cls.pg.fetchrow(query)

            if db_item['type'] != item['type']:
                raise ValidationError

            if not db_item:
                insert_items.append(item)
            else:
                update_items.append(item)

                if db_item['parent_id']:
                    update_parents[db_item['parent_id']][0] = update_parents.get(db_item['parent_id'])[0] - item['price']
                    update_parents[db_item['parent_id']][1] = update_parents.get(db_item['parent_id'])[1] - 1
                if item['parentId']:
                    parent_query = items_table.select('type').where(items_table.c.item_id == item['parentId'])
                    parent = await cls.pg.fetchrow(parent_query)
                    if parent['type'] != 'CATEGORY':
                        raise ValidationError
                    
                    update_parents[item['parentId']][0] = update_parents.get(item['parentId'])[0] + item['price']
                    update_parents[db_item['parentId']][1] = update_parents.get(item['parentId'])[1] + 1

        return insert_items, update_items, update_parents
    
    @classmethod
    async def process_ancestors(cls, parents, date):
        ancestors = []
        updated_ancestors = []
        for key, item in parents:
            query = text(
                """    
                WITH RECURSIVE parents AS (
                    SELECT item_id, name, date, type, price_sum, price_amount, parent_id
                    FROM items
                    WHERE item_id = {}
                    UNION
                    SELECT op.item_id, op.name, op.date, op.type, op.price_sum, op.price_amount, op.parent_id
                    FROM items op
                    JOIN parents p ON op.item_id = p.parent_id
                )
                SELECT parents.item_id, parents.name, parents.date, parents.type,
                    parents.price_sum, parents.price_amount, parents.parent_id
                from PARENTS;""".format(key)
            )
            rows = await cls.pg.fetch(query)
            ancestors.append(**rows)
            for row in rows:
                row['price_sum'] += item[0]
                row['price_amount'] += item[1]
                row['date'] = date
                updated_ancestors.append(row)

        return ancestors, updated_ancestors


    @docs(summary='Добавить выгрузку с информацией о товарах/категориях')
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.transaction() as conn:
            items = self.request['data']['items']
            date = self.request['data']['date']

            insert_items, update_items, parents = self.divide_insert_update_items(items)

            # Вставка новых категорий/продуктов
            insert_rows = self.make_items_rows(insert_items, date)
            chunked_insert_rows = chunk_list(insert_rows, self.MAX_ITEMS_PER_INSERT)

            query = items_table.insert()
            for chunk in chunked_insert_rows:
                await conn.execute(query.values(list(chunk)))

            # Добавление категорий/продуктов статистику
            update_items_ids = [item['id'] for item in update_items]
            query = items_table.select().where(items_table.c.item_id._in.update_items_ids)
            statistics_items = await conn.execute(query)
            chunked_statistics_rows = chunk_list(statistics_items, self.MAX_ITEMS_PER_INSERT)

            query = stats_table.insert()
            for chunk in chunked_statistics_rows:
                await conn.execute(query.values(list(chunk)))

            # Обновление категорий/продуктов
            update_rows = self.make_items_rows(update_items, date)
            chunked_update_rows = chunk_list(update_rows, self.MAX_ITEMS_PER_INSERT)

            query = items_table.update().where(items_table.c.item_id == bindparam('item_id'))
            for chunk in chunked_update_rows:
                await conn.execute(query.values(list(chunk)))

            # Нахождение предков категорий/продуктов
            ancestors, updated_ancestors = self.process_ancestors(parents, date)

            # Добавление предков категорий/продуктов в статистику
            chunked_statistics_rows = chunk_list(ancestors, self.MAX_ITEMS_PER_INSERT)
            query = stats_table.insert()
            for chunk in chunked_statistics_rows:
                await conn.execute(query.values(list(chunk)))

            # Обновление предков категорий/продуктов
            chunked_ancestor_rows = chunk_list(updated_ancestors, self.MAX_ITEMS_PER_INSERT)
            query = items_table.update().where(items_table.c.item_id == bindparam('item_id'))
            for chunk in chunked_ancestor_rows:
                await conn.execute(query.values(list(chunk)))

        return Response(status=HTTPStatus.OK)


