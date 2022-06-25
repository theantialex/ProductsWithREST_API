from http import HTTPStatus
from aiohttp.web_response import Response
from aiohttp_apispec import docs, response_schema
from .base import BaseView
from products_app.db.schema import items_table
from aiohttp.web_exceptions import HTTPNotFound
from products_app.api.schema import NodeInfoSchema
from datetime import datetime
from sqlalchemy.dialects import postgresql

class NodesView(BaseView):
    URL = r'/nodes/{id}'

    @property
    def id(self):
        return str(self.request.match_info.get('id'))

    @classmethod
    def make_item_responce(self, item, children):
        price = None
        if item['price_sum']:
            price = item['price_sum'] // item['price_amount']
        
        return {
            'id': item['item_id'],
            'name': item['name'],
            'type': item['type'],
            'parentId': item['parent_id'],
            'date': datetime.isoformat(item['date'], timespec='milliseconds') + 'Z',
            'price': price,
            'children': children
        }
    
    async def get_children(self, item):
        query = items_table.select().distinct(items_table.c.item_id).where(items_table.c.parent_id == item['item_id']) \
                .order_by(items_table.c.item_id, items_table.c.date.desc())
        rows = await self.pg.fetch(self.get_sql(query, postgresql.dialect()))

        children = []
        for row in rows:
            children.append(self.make_item_responce(row, None))

            if row['type'] == 'CATEGORY':
                children[-1]['children'] = await self.get_children(row)

        if not children:
            return None
        return children


    @docs(summary='Получить информацию о категории/продукте')
    @response_schema(NodeInfoSchema())
    async def get(self):
        query = items_table.select().where(items_table.c.item_id == self.id).order_by(items_table.c.date.desc())

        db_item = await self.pg.fetchrow(self.get_sql(query))
        if not db_item:
            raise HTTPNotFound(text="Item not found")

        children = await self.get_children(db_item)
        item = self.make_item_responce(db_item, children)

        return Response(status=HTTPStatus.OK, body=item)
