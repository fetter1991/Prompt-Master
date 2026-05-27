"""add_model_type_to_image

Revision ID: b7c9a1d2e3f4
Revises: 651f709df303, 5ad3ba017004
Create Date: 2026-05-27 11:16:30.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c9a1d2e3f4'
down_revision = ('651f709df303', '5ad3ba017004')
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('image', schema=None) as batch_op:
        batch_op.add_column(sa.Column('model_type', sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f('ix_image_model_type'), ['model_type'], unique=False)


def downgrade():
    with op.batch_alter_table('image', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_image_model_type'))
        batch_op.drop_column('model_type')
