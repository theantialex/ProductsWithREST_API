from datetime import datetime

from marshmallow import Schema, ValidationError, validates, validates_schema
from marshmallow.fields import DateTime, Int, Nested, Str
from marshmallow.validate import Length, OneOf, Range

from products_app.db.schema import ItemType

class ItemImportSchema(Schema):
    id = Str(validate=Length(min=1, max=256), required=True)
    name = Str(validate=Length(min=1, max=256), required=True)
    parentId = Str(allow_none=True, validate=Length(min=1, max=256), required=False)
    price = Int(allow_none=True, validate=Range(min=0), strict=True, required=False)
    type = Str(validate=OneOf([type.value for type in ItemType]), required=True)

class ItemSchema(ItemImportSchema):
    date = DateTime(required=True)
    children = Nested(lambda: ItemSchema(), many=True, required=False)


class ImportSchema(Schema):
    items = Nested(ItemImportSchema, many=True, required=True)
    updateDate = DateTime(required=True)

    @validates('updateDate')
    def validate_update_date(self, value: datetime):
        if value > datetime.now():
            raise ValidationError("Update date can't be in future")

    @validates_schema
    def validate_items(self, data, **_):
        item_ids = set()
        for item in data['items']:
            if item['id'] in item_ids:
                raise ValidationError(
                    'item id %r is not unique' % item['id']
                )
            if item['parentId'] == item['id']:
                raise ValidationError(
                    'parent id {} cannot be the same as item id {}'.format(item['parentId'], item['id'])
                )
            if not item['price'] and item['type'] != 'CATEGORY':
                raise ValidationError(
                    'offer price cannot be null'
            )
            if item['type'] == 'CATEGORY' and item['price']:
                raise ValidationError(
                    'category price must be null'
            )
            item_ids.add(item['id'])

