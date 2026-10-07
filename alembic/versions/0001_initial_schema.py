"""Initial schema for files and measurements tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'files',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', name='fileprocessingstatus'), nullable=False),
        sa.Column('source_crs', sa.String(length=100), nullable=True),
        sa.Column('feature_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'measurements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('feature_id', sa.Integer(), nullable=False),
        sa.Column('geometry_type', sa.String(length=50), nullable=False),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('measurement_type', sa.String(length=50), nullable=True),
        sa.Column('measurement_value', sa.Float(), nullable=True),
        sa.Column('measurement_unit', sa.String(length=20), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_measurements_file_id'), 'measurements', ['file_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_measurements_file_id'), table_name='measurements')
    op.drop_table('measurements')
    op.drop_table('files')
