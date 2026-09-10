"""create invoices table

Revision ID: 0001_create_invoices_table
Revises: 
Create Date: 2026-09-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_invoices_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invoice',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('source_file_key', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('vendor_name', sa.String(), nullable=True),
        sa.Column('invoice_number', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('invoice')
