from http import HTTPStatus
from aiohttp.web_response import Response
from aiohttp_apispec import docs, request_schema
from .base import BaseView
from products_app.db.schema import items_table
from aiohttp.web_exceptions import HTTPNotFound
from sqlalchemy import exists, select, delete
from products_app.api.schema import ItemSchema



class NodesView(BaseView):
    URL = r'/nodes/{id:\w+}'

    @property
    def id(self):
        return str(self.request.match_info.get('id'))
"""
    @docs(summary='Получить информацию о категории/продукте')
    @request_schema(FullItemSchema())
    async def get(self):
        query = items_table.select().where(items_table.c.item_id == self.id)

        item = await self.pg.fetchrow(query)
        if not item:
            raise HTTPNotFound(text="Item not found")
        
        query = select([
            exists().where(items_table.c.parent_id == self.id)
        ])

        item['children'] = await self.pg.fetch(query)

        return Response(status=HTTPStatus.OK, body=item)
"""