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
        async with self.pg.acquire() as conn:
            async with conn.transaction():

                query = items_table.select().where(items_table.c.item_id == self.id).order_by(items_table.c.date.desc())
                item = await conn.fetchrow(self.get_sql(query))
                if not item:
                    raise HTTPNotFound(text="Item not found")

                update_query = """ WITH updates AS (WITH RECURSIVE parents AS (
                                (SELECT item_id, date, parent_id
                                    FROM items
                                    WHERE item_id = $1::varchar ORDER BY date DESC LIMIT 1)
                                UNION
                                (SELECT op.item_id, op.date, op.parent_id
                                    FROM items op
                                    JOIN parents p ON op.item_id = p.parent_id))
                                SELECT DISTINCT ON (parents.item_id) parents.item_id, parents.date, parents.parent_id
                                FROM parents
                                ORDER BY parents.item_id, parents.date DESC)
                                UPDATE items SET
                                    price_sum=items.price_sum-$2,
                                    price_amount=items.price_amount-1
                                FROM updates
                                where items.item_id=updates.item_id and items.date=updates.date;
                            """
                if item['parent_id'] and item['price_sum']:
                    await conn.execute(update_query, item['parent_id'], item['price_sum'])

                delete_query = """ WITH RECURSIVE parents AS (
                                    (SELECT item_id, parent_id
                                        FROM items
                                        WHERE item_id = $1::varchar)
                                    UNION
                                    (SELECT op.item_id, op.parent_id
                                        FROM items op
                                        JOIN parents p ON op.parent_id = p.item_id))
                                DELETE FROM items WHERE items.item_id IN (SELECT parents.item_id FROM parents)
                            """
                if item['type'] == 'OFFER':
                    query = delete(items_table).where(items_table.c.item_id == self.id)
                    await conn.execute(self.get_sql(query))
                else:
                    await conn.execute(delete_query, self.id)

        return Response(status=HTTPStatus.OK)