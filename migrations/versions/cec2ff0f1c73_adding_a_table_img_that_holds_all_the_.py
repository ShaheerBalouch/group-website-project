"""Adding a table Img that holds all the images, and instead of strings in the other tables, its a reference to an object from this table.

Revision ID: cec2ff0f1c73
Revises: 3827b39705df
Create Date: 2022-02-25 20:47:19.075680

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'cec2ff0f1c73'
down_revision = '3827b39705df'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('img',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('img', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('mimetype', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('img')
    )
    op.add_column('tools', sa.Column('image', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'tools', 'img', ['image'], ['id'])
    op.drop_column('tools', 'image_file')
    op.add_column('user', sa.Column('image', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'user', 'img', ['image'], ['id'])
    op.drop_column('user', 'image_file')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('image_file', mysql.VARCHAR(length=40), nullable=False))
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.drop_column('user', 'image')
    op.add_column('tools', sa.Column('image_file', mysql.VARCHAR(length=40), nullable=False))
    op.drop_constraint(None, 'tools', type_='foreignkey')
    op.drop_column('tools', 'image')
    op.drop_table('img')
    # ### end Alembic commands ###