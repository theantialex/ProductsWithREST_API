from .base import BaseView
from products_app.utils.pg import MAX_QUERY_ARGS
from products_app.db.schema import items_table, stats_table
from products_app.api.schema import ImportSchema

from http import HTTPStatus
from typing import Generator

from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from aiomisc import chunk_list

"""
class ImportsView(BaseView):
    URL = '/imports'
    MAX_CITIZENS_PER_INSERT = MAX_QUERY_ARGS // len(items_table.columns)

    @classmethod
    def make_new_items_rows(cls, items, date) -> Generator:
        \"""
        Генерирует данные готовые для вставки в таблицу items.
        \"""
        for item in items:
            if item['price']:
                item['price_amount'] = 1
            else:
                item['price_amount'] = sum(i['parentId'] == item['id'] for i in items)
            yield {
                'item_id': item['id'],
                'name': item['name'],
                'date': date,
                'type': item['type'],
                'parent_id': item['parentId'],
                'price_sum': item['price'],
                'price_amount': item['price_amount']
            }


    @docs(summary='Добавить выгрузку с информацией о товарах/категориях')
    @request_schema(ImportSchema())
    async def post(self):
        async with self.pg.transaction() as conn:


        return Response(status=HTTPStatus.OK)

"""
