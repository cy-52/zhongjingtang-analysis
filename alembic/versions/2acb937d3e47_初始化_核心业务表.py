"""初始化：核心业务表

Revision ID: 2acb937d3e47
Revises: 
Create Date: 2026-07-08 14:27:12.547970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2acb937d3e47'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("product_categories",
        sa.Column("category_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.PrimaryKeyConstraint("category_id"),
    )
    op.create_table("products",
        sa.Column("product_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10,2), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), server_default="available"),
        sa.Column("quantity", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_table("product_category_relationship",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("product_id", "category_id"),
    )
    op.create_table("users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("balance", sa.Numeric(10,2), server_default="0.00"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table("orders",
        sa.Column("order_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total", sa.Numeric(10,2), nullable=False),
        sa.Column("discount", sa.Numeric(10,2), server_default="0.00"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.PrimaryKeyConstraint("order_id"),
    )
    op.create_table("order_items",
        sa.Column("order_item_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("order_item_id"),
    )
    op.create_table("inventory",
        sa.Column("inventory_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(10,2), nullable=False),
        sa.Column("supplier_info", sa.String(255)),
        sa.PrimaryKeyConstraint("inventory_id"),
    )
    op.create_table("payment_channels",
        sa.Column("channel_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("channel_id"),
    )
    op.create_table("payments",
        sa.Column("payment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10,2), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("payment_time", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("transaction_id", sa.String(255), unique=True),
        sa.Column("payment_method", sa.String(100)),
        sa.PrimaryKeyConstraint("payment_id"),
    )

def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("payment_channels")
    op.drop_table("inventory")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("users")
    op.drop_table("product_category_relationship")
    op.drop_table("products")
    op.drop_table("product_categories")
