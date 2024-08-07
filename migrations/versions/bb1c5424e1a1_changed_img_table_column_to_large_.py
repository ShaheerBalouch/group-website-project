"""Changed img table column to large binary instead of text

Revision ID: bb1c5424e1a1
Revises: f1eca4575b38
Create Date: 2022-02-26 00:19:52.800323

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'bb1c5424e1a1'
down_revision = 'f1eca4575b38'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('img', 'img',
               existing_type=mysql.TEXT(),
               nullable=True)
    op.drop_index('img', table_name='img')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('img', 'img', ['img'], unique=True)
    op.alter_column('img', 'img',
               existing_type=mysql.TEXT(),
               nullable=False)
    # ### end Alembic commands ###
