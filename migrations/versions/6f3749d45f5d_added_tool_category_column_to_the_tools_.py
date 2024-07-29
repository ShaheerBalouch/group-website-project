"""Added tool category column to the tools table

Revision ID: 6f3749d45f5d
Revises: b3b1e7cd5e25
Create Date: 2022-04-22 02:29:42.272336

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f3749d45f5d'
down_revision = 'b3b1e7cd5e25'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tools', sa.Column('tool_category', sa.String(length=100), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tools', 'tool_category')
    # ### end Alembic commands ###