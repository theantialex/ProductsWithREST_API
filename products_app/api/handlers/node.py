from .base import BaseView
from aiohttp_apispec import docs, response_schema
from datetime import datetime
from aiohttp.web_response import Response
from products_app.db.schema import items_table
from marshmallow import ValidationError
from http import HTTPStatus
from sqlalchemy import and_
from aiohttp.web_exceptions import HTTPNotFound
from sqlalchemy import exists, select
from products_app.api.schema import StatisticsSchema
from dateutil import parser

class NodeView(BaseView):
    URL = r'/node/{id}/statistic'

    @property
    def id(self):
        return str(self.request.match_info.get('id'))
    
    @classmethod
    def make_items_list(cls, rows):
        items = []
        for row in rows:
            if row['type'] == 'CATEGORY':
                price = row['price_sum'] // row['price_amount'] if row['price_sum'] else None
            else:
                price = row['price_sum']
            items.append(
                {
                    'id': row['item_id'],
                    'name': row['name'],
                    'date': datetime.isoformat(row['date'], timespec='milliseconds') + 'Z',
                    'parentId': row['parent_id'],
                    'price': price,
                    'type': row['type']
                }
            )
        return {'items' : items}

    @docs(summary='Получить статистику в периоде по категории/товару')
    @response_schema(StatisticsSchema())
    async def get(self):
        try:
            date_start = self.request.rel_url.query.get('dateStart', '')
            date_end = self.request.rel_url.query.get('dateEnd', '')

            date_start = parser.isoparse(date_start)
            date_end = parser.isoparse(date_end)
            if date_start.timestamp() > datetime.now().timestamp() or date_end.timestamp() > datetime.now().timestamp() \
                 or date_start.timestamp() > date_end.timestamp():
                raise ValidationError
        except:
            raise ValidationError('Validation Failed')
        
        exists_query = select([
            exists().where(items_table.c.item_id == self.id)
        ])

        item = await self.pg.fetchval(self.get_sql(exists_query))
        if not item:
            raise HTTPNotFound(text="Item not found")

        query = items_table.select().where(and_(items_table.c.item_id == self.id, 
            str(date_start) <= items_table.c.date, items_table.c.date < str(date_end))).order_by(items_table.c.date)     
        rows = await self.pg.fetch(self.get_sql(query))

        items_list = self.make_items_list(rows)

        return Response(status=HTTPStatus.OK, body=items_list)