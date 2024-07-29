"""Changing the address table's columns, and removing the postcode column from the user table, as it's already in address.

Revision ID: 5fe194e70db4
Revises: e50bb4b8faf6
Create Date: 2022-03-09 03:39:17.324216

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5fe194e70db4'
down_revision = 'e50bb4b8faf6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('address', sa.Column('address_line_1', sa.String(length=100), nullable=True))
    op.drop_column('address', 'country')
    op.drop_column('address', 'full_address')
    op.drop_column('user', 'postcode')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('postcode', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64), nullable=False))
    op.add_column('address', sa.Column('full_address', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True))
    op.add_column('address', sa.Column('country', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True))
    op.drop_column('address', 'address_line_1')
    # ### end Alembic commands ###