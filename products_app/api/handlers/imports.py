from .base import BaseView
from products_app.utils.pg import MAX_QUERY_ARGS
from products_app.db.schema import items_table, stats_table
from products_app.api.schema import ImportSchema

from http import HTTPStatus
from typing import Generator

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from aiomisc import chunk_list
from sqlalchemy import exists, select, bindparam


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
        for item in items:
            query = select([
                exists().where(items_table.c.item_id == item.id)
            ])
            if not await cls.pg.fetchval(query):
                insert_items.append(item)
            else:
                update_items.append(item)
        return insert_items, update_items


    @docs(summary='Добавить выгрузку с информацией о товарах/категориях')
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.transaction() as conn:
            items = self.request['data']['items']
            date = self.request['data']['date']

            orphan_items = filter(lambda x: x['parentId'] == None, items)
            categorized_items = filter(lambda x: x['parentId'], items)

            orphan_insert_items, orphan_update_items = self.divide_insert_update_items(orphan_items)
            categorized_insert_items, categorized_update_items = self.divide_insert_update_items(categorized_items)

            insert_rows = self.make_items_rows(orphan_insert_items, date)
            update_rows = self.make_items_rows(orphan_update_items, date)
            chunked_insert_rows = chunk_list(insert_rows, self.MAX_ITEMS_PER_INSERT)
            chunked_update_rows = chunk_list(update_rows, self.MAX_ITEMS_PER_INSERT)

            # Вставка новых категорий/продуктов без родителей
            query = items_table.insert()
            for chunk in chunked_insert_rows:
                await conn.execute(query.values(list(chunk)))
            
            update_items_ids = [item['item_id'] for item in orphan_update_items]
            chunked_statistics_rows = chunk_list(update_items_ids, self.MAX_ITEMS_PER_INSERT)

            # Вставка новых категорий/продуктов без родителей
            for chunk in chunked_statistics_rows:
                query = select(items_table).where(items_table.c.id._in(update_items_ids))
                rows = await conn.fetch(query.values(list(chunk)))
                stats_query = stats_table.insert().values(rows)
                await conn.execute(stats_query)

            # Обновление категорий/продуктов без родителей
            query = items_table.update().where(items_table.c.item_id == bindparam('item_id'))
            for chunk in chunked_update_rows:
                await conn.execute(query.values(list(chunk)))





        return Response(status=HTTPStatus.OK)


