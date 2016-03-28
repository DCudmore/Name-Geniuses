"""empty message

Revision ID: 7eef1dbad78e
Revises: 67373b1a981a
Create Date: 2016-03-28 09:06:21.644045

"""

# revision identifiers, used by Alembic.
revision = '7eef1dbad78e'
down_revision = '67373b1a981a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('totalpaid', sa.Float(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'totalpaid')
    ### end Alembic commands ###
