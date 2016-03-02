"""empty message

Revision ID: 865e69dc3f9f
Revises: abbac1ca8695
Create Date: 2016-02-29 12:14:42.762718

"""

# revision identifiers, used by Alembic.
revision = '865e69dc3f9f'
down_revision = 'abbac1ca8695'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('suggestion', sa.Column('timestamp_day', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('suggestion', 'timestamp_day')
    ### end Alembic commands ###