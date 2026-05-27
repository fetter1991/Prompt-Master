"""add_main_image_table

Revision ID: c2d4e6f8a0b1
Revises: b7c9a1d2e3f4
Create Date: 2026-05-27 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d4e6f8a0b1'
down_revision = 'b7c9a1d2e3f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'main_image',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('thumbnail_path', sa.String(length=255), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['image.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('main_image', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_main_image_image_id'), ['image_id'], unique=False)

    op.execute(
        "INSERT INTO main_image (image_id, file_path, thumbnail_path, position) "
        "SELECT id, file_path, thumbnail_path, 0 FROM image"
    )


def downgrade():
    with op.batch_alter_table('main_image', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_main_image_image_id'))
    op.drop_table('main_image')
