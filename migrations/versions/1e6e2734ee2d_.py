"""empty message

Revision ID: 1e6e2734ee2d
Revises: c25188309f0d
Create Date: 2016-02-15 11:36:11.243507

"""

# revision identifiers, used by Alembic.
revision = '1e6e2734ee2d'
down_revision = 'c25188309f0d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('totalwinnings', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'totalwinnings')
    ### end Alembic commands ###
