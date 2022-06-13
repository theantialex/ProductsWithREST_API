"""Initial

Revision ID: 84ce79b15ff4
Revises: 
Create Date: 2022-06-13 16:15:51.667484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84ce79b15ff4'
down_revision = None
branch_labels = None
depends_on = None

ItemType = sa.Enum('offer', 'category', name='item_type')

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('items',
    sa.Column('item_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('type', ItemType, nullable=False),
    sa.Column('price_sum', sa.Integer(), nullable=True),
    sa.Column('price_amount', sa.Integer(), nullable=True),
    sa.Column('parent_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['items.item_id'], name=op.f('fk__items__parent_id__items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', name=op.f('pk__items'))
    )
    op.create_index(op.f('ix__items__parent_id'), 'items', ['parent_id'], unique=False)
    op.create_table('statistics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('item_id', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('type', sa.Enum('offer', 'category', name='item_type'), nullable=False),
    sa.Column('price_sum', sa.Integer(), nullable=True),
    sa.Column('price_amount', sa.Integer(), nullable=True),
    sa.Column('parent_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['item_id'], ['items.item_id'], name=op.f('fk__statistics__item_id__items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__statistics'))
    )
    op.create_index(op.f('ix__statistics__item_id'), 'statistics', ['item_id'], unique=False)
    op.create_index(op.f('ix__statistics__parent_id'), 'statistics', ['parent_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix__statistics__parent_id'), table_name='statistics')
    op.drop_index(op.f('ix__statistics__item_id'), table_name='statistics')
    op.drop_table('statistics')
    op.drop_index(op.f('ix__items__parent_id'), table_name='items')
    op.drop_table('items')
    ItemType.drop(op.get_bind())
    # ### end Alembic commands ###
