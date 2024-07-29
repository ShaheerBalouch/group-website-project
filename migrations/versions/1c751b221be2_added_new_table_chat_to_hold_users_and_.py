"""Added new table chat to hold users and rooms between them. Also made the 2 user columns in messages foreign keys and removed the duplicate datetime column

Revision ID: 1c751b221be2
Revises: 6f3749d45f5d
Create Date: 2022-05-11 06:09:41.310600

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '1c751b221be2'
down_revision = '6f3749d45f5d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('chat',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_1', sa.Integer(), nullable=False),
    sa.Column('user_2', sa.Integer(), nullable=False),
    sa.Column('room', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['user_1'], ['user.id'], ),
    sa.ForeignKeyConstraint(['user_2'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_foreign_key(None, 'messages', 'user', ['to_user'], ['id'])
    op.create_foreign_key(None, 'messages', 'user', ['from_user'], ['id'])
    op.drop_column('messages', 'date')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('messages', sa.Column('date', mysql.DATETIME(), nullable=False))
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.drop_table('chat')
    # ### end Alembic commands ###
