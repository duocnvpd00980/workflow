"""Add aliases to hotel_room

Revision ID: xxxxxx
Revises: 
Create Date: 2026-06-10 XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


revision = 'xxxxxx'  # giữ nguyên
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('hotel_room', sa.Column('aliases', sa.JSON(), nullable=True, server_default='[]'))


def downgrade() -> None:
    op.drop_column('hotel_room', 'aliases')