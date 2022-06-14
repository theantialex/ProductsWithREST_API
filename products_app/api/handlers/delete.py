from http import HTTPStatus
from aiohttp.web_response import Response
from aiohttp_apispec import docs
from .base import BaseView
from products_app.db.schema import items_table
from aiohttp.web_exceptions import HTTPNotFound
from sqlalchemy import exists, select, delete



class DeleteView(BaseView):
    URL = r'/delete/{id:\w+}'

    @property
    def id(self):
        return str(self.request.match_info.get('id'))

    docs(summary='Удалить продукта/категории')
    async def delete(self):
        query = select([
            exists().where(items_table.c.item_id == self.id)
        ])
        if not await self.pg.fetchval(query):
            raise HTTPNotFound(text="Item not found")
        
        query = delete(items_table).where(items_table.c.item_id == self.id)
        await self.pg.execute(query)
        return Response(status=HTTPStatus.OK)