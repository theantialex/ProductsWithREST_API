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
    def make_items_rows(cls, items, date):
        """
        Генерирует данные готовые для вставки в таблицу items.
        """
        rows = []
        for item in items:
            item['price_amount'] = 0
            if item['price']:
                item['price_amount'] = 1
            rows.append({
                'item_id': item['id'],
                'name': item['name'],
                'date': date,
                'type': item['type'],
                'parent_id': item['parentId'],
                'price_sum': item['price'],
                'price_amount': item['price_amount']
            })
        return rows
    
    async def calculate_parent_updates(self, items):
        imported_items = {}
        update_parents = {}
        for item in items:
            query = items_table.select().where(items_table.c.item_id == item['id']).order_by(items_table.c.date.desc())
            db_item = await self.pg.fetchrow(self.get_sql(query))

            if db_item and db_item['type'] != item['type']:
                raise ValidationError('Validation Failed')

            if db_item and db_item['parent_id']:
                if db_item['parent_id'] in update_parents and db_item['type'] == 'OFFER':
                    parent = update_parents[db_item['parent_id']]
                    update_parents[db_item['parent_id']] = [parent[0] - db_item['price_sum'], parent[1] - 1]
                elif db_item['parent_id'] not in update_parents and db_item['type'] == 'OFFER':
                        update_parents[db_item['parent_id']] = [-db_item['price_sum'], -1]

            if item['parentId']:
                parent_query = items_table.select().where(items_table.c.item_id == item['parentId']).order_by(items_table.c.date.desc())
                parent = await self.pg.fetchrow(self.get_sql(parent_query))
                if (not parent or parent['type'] != 'CATEGORY') and \
                    (item['parentId'] not in imported_items or imported_items[item['parentId']]['type'] != 'CATEGORY'):
                    raise ValidationError('Validation Failed')

                if item['parentId'] in update_parents and item['type'] == 'OFFER':
                    parent = update_parents[item['parentId']]
                    update_parents[item['parentId']] = [parent[0] + item['price'], parent[1] + 1]
                elif item['parentId'] not in update_parents and item['type'] == 'OFFER':
                    update_parents[item['parentId']] = [item['price'], 1]
                
                parent_id = item['parentId']
                while parent_id and parent_id in imported_items:
                    parent_id = imported_items[parent_id]['parentId']
                    if parent_id and parent_id in update_parents:
                        update_parents[parent_id] = [update_parents[parent_id][0] + update_parents[item['parentId']][0], 
                            update_parents[parent_id][1] + update_parents[item['parentId']][1]]
                    elif parent_id and parent_id in imported_items:
                        update_parents[parent_id] = [update_parents[item['parentId']][0], update_parents[item['parentId']][1]]
            imported_items[item['id']] = item
        return update_parents

    async def make_ancestors_rows(self, parents, date, ids):
        """
        Генерирует данные готовые для вставки в таблицу items.
        """
        insert_ancestors = []
        update_ancestors = {}
        updates ={}
        for key, item in parents.items():
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

            rows = await self.pg.fetch(query, key)
            for row in rows:
                row = dict(row)
                log.info(str(row.items()))

                if row['item_id'] not in updates:
                    updates[row['item_id']] = [item[0], item[1]]
                    if row['item_id'] in ids:
                        update_ancestors[row['item_id']] = [row['price_sum'], row['price_amount']]
                    else:
                        insert_ancestors.append(row)
                else:
                    updates[row['item_id']] = [updates[row['item_id']][0]+item[0], updates[row['item_id']][1]+ item[1]]
                row['date'] = date

        for ins in insert_ancestors:
            if ins['price_sum']:
                ins['price_sum'] += updates[ins['item_id']][0]
            else:
                ins['price_sum'] = updates[ins['item_id']][0]
            ins['price_amount'] += updates[ins['item_id']][1]

        for key in update_ancestors.keys():
            if update_ancestors[key][0]:
                update_ancestors[key][0] += updates[key][0]
            else:
                update_ancestors[key][0] = updates[key][0]
            update_ancestors[key][1] += updates[key][1]

        for key, val in parents.items():
            if key not in update_ancestors and key in ids:
                update_ancestors[key] = [val[0], val[1]]

        return update_ancestors, insert_ancestors


    @docs(summary='Добавить выгрузку с информацией о товарах/категориях')
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.acquire() as conn:
            async with conn.transaction():

                items = self.request['data']['items']
                date = self.request['data']['updateDate']
                ids = [item['id'] for item in items]

                # Нахождение обновлений родителей категорий/продуктов
                parent_updates = await self.calculate_parent_updates(items)

                # Нахождение предков категорий/продуктов
                update_ancestors, insert_ancestors = await self.make_ancestors_rows(parent_updates, date, ids)

                # Вставка обновленных предков категорий/продуктов
                chunked_ancestor_rows = chunk_list(insert_ancestors, self.MAX_ITEMS_PER_INSERT)
                for chunk in chunked_ancestor_rows:
                    query = items_table.insert().values(chunk)
                    await conn.execute(self.get_sql(query))

                # Получение импортированных категорий/продуктов для вставки
                insert_rows = self.make_items_rows(items, date)

                # Обновление предков категорий/продуктов, которые присутстуют в import
                for key, val in update_ancestors.items():
                    id = ids.index(key)
                    insert_rows[id]['price_sum'] = val[0]
                    insert_rows[id]['price_amount'] = val[1]
                
                # Вставка всех импортированных категорий/продуктов
                chunked_insert_rows = chunk_list(insert_rows, self.MAX_ITEMS_PER_INSERT)
                for chunk in chunked_insert_rows:
                    query = items_table.insert().values(chunk)
                    await conn.fetchval(self.get_sql(query))

                return Response(status=HTTPStatus.OK)


