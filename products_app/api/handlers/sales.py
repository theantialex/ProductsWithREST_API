from datetime import datetime, timedelta
from dateutil import parser
from marshmallow import ValidationError
from sqlalchemy import and_
from .base import BaseView
from aiohttp_apispec import docs, response_schema
from products_app.db.schema import items_table
from datetime import datetime
from aiohttp.web_response import Response
from sqlalchemy.dialects import postgresql
from http import HTTPStatus
from products_app.api.schema import StatisticsSchema

class SalesView(BaseView):
    URL = '/sales'

    @classmethod
    def make_items_list(cls, rows):
        items = []
        for row in rows:
            items.append(
                {
                    'id': row['item_id'],
                    'name': row['name'],
                    'date': datetime.isoformat(row['date'], timespec='milliseconds') + 'Z',
                    'parentId': row['parent_id'],
                    'price': row['price_sum'],
                    'type': row['type']
                }
            )
        return {'items' : items}

    @docs(summary='Получить список обновленных товаров')
    @response_schema(StatisticsSchema())
    async def get(self):
        try:
            date = self.request.rel_url.query.get('date', '')
            date = parser.isoparse(date)
            if date.timestamp() > datetime.now().timestamp():
                raise ValidationError
        except:
            raise ValidationError('Validation Failed')

        query = items_table.select().distinct(items_table.c.item_id).where(and_(items_table.c.type == 'OFFER', 
            str(date - timedelta(hours=24)) <= items_table.c.date, items_table.c.date <= str(date))) \
                .order_by(items_table.c.item_id, items_table.c.date.desc())
        
        rows = await self.pg.fetch(self.get_sql(query, postgresql.dialect()))
        items_list = self.make_items_list(rows)

        return Response(status=HTTPStatus.OK, body=items_list)
