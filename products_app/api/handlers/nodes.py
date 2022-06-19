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

    @classmethod
    def make_item_responce(self, item, children):
        return {
            'id': item['item_id'],
            'name': item['name'],
            'type': item['type'],
            'parentId': item['parent_id'],
            'date': item['date'],
            'price': item['price_sum'],
            'children': children
        }

    @classmethod
    def make_childfree_item(self, item):
        return {
            'id': item['item_id'],
            'name': item['name'],
            'type': item['type'],
            'parentId': item['parent_id'],
            'date': item['date'],
            'price': item['price_sum']
        }
    
    async def get_children(self, item):
        query = items_table.select().distinct(items_table.c.item_id).where(items_table.c.parent_id == item['item_id']) \
                .order_by(items_table.c.item_id, items_table.c.date.desc())
        rows = await self.pg.fetch(self.get_sql(query))

        children = []
        for row in rows:
            print(self.make_childfree_item(row))
            children.append(self.make_childfree_item(row))
            print(children)
            if row['type'] == 'CATEGORY':
                children[-1]['children'] = await self.get_children(row)

        if not children:
            return None
        return children


    @docs(summary='Получить информацию о категории/продукте')
    async def get(self):

        query = items_table.select().where(items_table.c.item_id == self.id).order_by(items_table.c.date.desc())
        db_item = await self.pg.fetchrow(self.get_sql(query))
        if not db_item:
            raise HTTPNotFound(text="Item not found")
        
        print(db_item)

        children = await self.get_children(db_item)
        item = self.make_item_responce(db_item, children)

        return Response(status=HTTPStatus.OK, body=item)
