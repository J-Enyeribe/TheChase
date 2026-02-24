"""initial schema — dual currency + order lifecycle

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── Create enum types safely in PostgreSQL ──
    # PostgreSQL does not support CREATE TYPE IF NOT EXISTS,
    # so we use a PL/pgSQL DO block to catch duplicate_object errors.
    enums = {
        "currency": "('KSH', 'UGX')",
        "userrole": "('admin', 'manager', 'cashier', 'waiter')",
        "orderstatus": "('placed', 'served', 'cleared')",
        "transactionstatus": "('pending', 'completed', 'voided', 'refunded')",
        "paymentmethod": "('cash', 'card', 'mobile_money', 'credit')",
        "purchaseorderstatus": "('draft', 'sent', 'partially_received', 'received', 'cancelled')",
        "movementtype": "('purchase', 'sale', 'adjustment', 'return_in', 'return_out', 'damage')"
    }

    for name, values in enums.items():
        op.execute(f"""
            DO $$
            BEGIN
                CREATE TYPE {name} AS ENUM {values};
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)

    # Enum references used in table columns.
    # We use PostgreSQL's specific ENUM class which strictly obeys create_type=False
    currency_enum            = ENUM("KSH", "UGX",                                                          name="currency",            create_type=False)
    userrole_enum            = ENUM("admin", "manager", "cashier", "waiter",                               name="userrole",            create_type=False)
    orderstatus_enum         = ENUM("placed", "served", "cleared",                                         name="orderstatus",         create_type=False)
    transactionstatus_enum   = ENUM("pending", "completed", "voided", "refunded",                          name="transactionstatus",   create_type=False)
    paymentmethod_enum       = ENUM("cash", "card", "mobile_money", "credit",                              name="paymentmethod",       create_type=False)
    purchaseorderstatus_enum = ENUM("draft", "sent", "partially_received", "received", "cancelled",        name="purchaseorderstatus", create_type=False)
    movementtype_enum        = ENUM("purchase", "sale", "adjustment", "return_in", "return_out", "damage", name="movementtype",        create_type=False)

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("full_name",       sa.String(120),             nullable=False),
        sa.Column("email",           sa.String(200),             nullable=False),
        sa.Column("hashed_password", sa.String(255),             nullable=False),
        sa.Column("role",            userrole_enum,              nullable=False, server_default="cashier"),
        sa.Column("is_active",       sa.Boolean(),               nullable=False, server_default="true"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # ── categories ───────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id",          sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("name",        sa.String(100),             nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── suppliers ────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id",           sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("name",         sa.String(200),             nullable=False),
        sa.Column("contact_name", sa.String(120)),
        sa.Column("phone",        sa.String(30)),
        sa.Column("email",        sa.String(200)),
        sa.Column("address",      sa.Text()),
        sa.Column("is_active",    sa.Boolean(),               nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── products ─────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id",              sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("sku",             sa.String(60),              nullable=False),
        sa.Column("name",            sa.String(200),             nullable=False),
        sa.Column("description",     sa.Text()),
        sa.Column("category_id",     sa.Integer(),               sa.ForeignKey("categories.id")),
        sa.Column("supplier_id",     sa.Integer(),               sa.ForeignKey("suppliers.id")),
        sa.Column("unit_price_ksh",  sa.Numeric(12, 2),          nullable=False),
        sa.Column("unit_price_ugx",  sa.Numeric(12, 2),          nullable=False),
        sa.Column("cost_price_ksh",  sa.Numeric(12, 2),          nullable=False),
        sa.Column("tax_rate",        sa.Numeric(5, 2),           nullable=False, server_default="0.00"),
        sa.Column("unit_of_measure", sa.String(30),              server_default="piece"),
        sa.Column("barcode",         sa.String(100)),
        sa.Column("is_active",       sa.Boolean(),               nullable=False, server_default="true"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("barcode"),
    )

    # ── inventory ────────────────────────────────────────────────────────
    op.create_table(
        "inventory",
        sa.Column("id",               sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("product_id",       sa.Integer(),               sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(12, 3),          nullable=False, server_default="0"),
        sa.Column("reorder_point",    sa.Numeric(12, 3),          nullable=False, server_default="10"),
        sa.Column("reorder_quantity", sa.Numeric(12, 3),          nullable=False, server_default="50"),
        sa.Column("location",         sa.String(100)),
        sa.Column("last_updated",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )

    # ── customers ────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id",          sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("full_name",   sa.String(120),             nullable=False),
        sa.Column("phone",       sa.String(30)),
        sa.Column("email",       sa.String(200)),
        sa.Column("loyalty_pts", sa.Integer(),               nullable=False, server_default="0"),
        sa.Column("is_active",   sa.Boolean(),               nullable=False, server_default="true"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
        sa.UniqueConstraint("email"),
    )

    # ── orders ───────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id",            sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("order_number",  sa.String(30),              nullable=False),
        sa.Column("currency",      currency_enum,              nullable=False),
        sa.Column("customer_id",   sa.Integer(),               sa.ForeignKey("customers.id")),
        sa.Column("table_ref",     sa.String(50)),
        sa.Column("status",        orderstatus_enum,           nullable=False, server_default="placed"),
        sa.Column("placed_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("placed_by_id",  sa.Integer(),               sa.ForeignKey("users.id"), nullable=False),
        sa.Column("served_at",     sa.DateTime(timezone=True)),
        sa.Column("served_by_id",  sa.Integer(),               sa.ForeignKey("users.id")),
        sa.Column("cleared_at",    sa.DateTime(timezone=True)),
        sa.Column("cleared_by_id", sa.Integer(),               sa.ForeignKey("users.id")),
        sa.Column("subtotal",       sa.Numeric(14, 2),         nullable=False, server_default="0"),
        sa.Column("tax_total",      sa.Numeric(14, 2),         nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(14, 2),         nullable=False, server_default="0"),
        sa.Column("grand_total",    sa.Numeric(14, 2),         nullable=False, server_default="0"),
        sa.Column("notes",         sa.Text()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )

    # ── order_items ──────────────────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id",         sa.Integer(),      autoincrement=True, nullable=False),
        sa.Column("order_id",   sa.Integer(),      sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(),      sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity",   sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount",   sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes",      sa.Text()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── transactions ─────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id",             sa.BigInteger(),            autoincrement=True, nullable=False),
        sa.Column("receipt_number", sa.String(30),              nullable=False),
        sa.Column("order_id",       sa.Integer(),               sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("cashier_id",     sa.Integer(),               sa.ForeignKey("users.id"), nullable=False),
        sa.Column("currency",       currency_enum,              nullable=False),
        sa.Column("status",         transactionstatus_enum,     nullable=False, server_default="completed"),
        sa.Column("subtotal",       sa.Numeric(14, 2),          nullable=False, server_default="0"),
        sa.Column("tax_total",      sa.Numeric(14, 2),          nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(14, 2),          nullable=False, server_default="0"),
        sa.Column("grand_total",    sa.Numeric(14, 2),          nullable=False, server_default="0"),
        sa.Column("notes",          sa.Text()),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_number"),
        sa.UniqueConstraint("order_id"),
    )

    # ── transaction_items ────────────────────────────────────────────────
    op.create_table(
        "transaction_items",
        sa.Column("id",             sa.Integer(),      autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.BigInteger(),   sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("product_id",     sa.Integer(),      sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity",       sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price",     sa.Numeric(12, 2), nullable=False),
        sa.Column("discount",       sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount",     sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_total",     sa.Numeric(14, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── payments ─────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id",             sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.BigInteger(),            sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("method",         paymentmethod_enum,         nullable=False),
        sa.Column("amount",         sa.Numeric(14, 2),          nullable=False),
        sa.Column("currency",       currency_enum,              nullable=False),
        sa.Column("reference",      sa.String(100)),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── purchase_orders ──────────────────────────────────────────────────
    op.create_table(
        "purchase_orders",
        sa.Column("id",            sa.Integer(),               autoincrement=True, nullable=False),
        sa.Column("po_number",     sa.String(30),              nullable=False),
        sa.Column("supplier_id",   sa.Integer(),               sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("status",        purchaseorderstatus_enum,   nullable=False, server_default="draft"),
        sa.Column("expected_date", sa.DateTime(timezone=True)),
        sa.Column("received_date", sa.DateTime(timezone=True)),
        sa.Column("total_cost",    sa.Numeric(14, 2),          nullable=False, server_default="0"),
        sa.Column("notes",         sa.Text()),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_number"),
    )

    # ── purchase_order_items ─────────────────────────────────────────────
    op.create_table(
        "purchase_order_items",
        sa.Column("id",                sa.Integer(),      autoincrement=True, nullable=False),
        sa.Column("purchase_order_id", sa.Integer(),      sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("product_id",        sa.Integer(),      sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity_ordered",  sa.Numeric(12, 3), nullable=False),
        sa.Column("quantity_received", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("unit_cost",         sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total",        sa.Numeric(14, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_order_id", "product_id", name="uq_po_product"),
    )

    # ── stock_movements ──────────────────────────────────────────────────
    op.create_table(
        "stock_movements",
        sa.Column("id",              sa.BigInteger(),            autoincrement=True, nullable=False),
        sa.Column("product_id",      sa.Integer(),               sa.ForeignKey("products.id"), nullable=False),
        sa.Column("user_id",         sa.Integer(),               sa.ForeignKey("users.id")),
        sa.Column("movement_type",   movementtype_enum,          nullable=False),
        sa.Column("quantity_change", sa.Numeric(12, 3),          nullable=False),
        sa.Column("quantity_before", sa.Numeric(12, 3),          nullable=False),
        sa.Column("quantity_after",  sa.Numeric(12, 3),          nullable=False),
        sa.Column("reference_id",    sa.String(60)),
        sa.Column("notes",           sa.Text()),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Indexes ──────────────────────────────────────────────────────────
    op.create_index("ix_products_sku",               "products",        ["sku"])
    op.create_index("ix_products_barcode",           "products",        ["barcode"])
    op.create_index("ix_orders_status",              "orders",          ["status"])
    op.create_index("ix_orders_placed_at",           "orders",          ["placed_at"])
    op.create_index("ix_orders_currency",            "orders",          ["currency"])
    op.create_index("ix_transactions_created_at",    "transactions",    ["created_at"])
    op.create_index("ix_transactions_currency",      "transactions",    ["currency"])
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])


def downgrade() -> None:
    for tbl in [
        "stock_movements", "purchase_order_items", "purchase_orders",
        "payments", "transaction_items", "transactions",
        "order_items", "orders",
        "inventory", "products", "customers", "suppliers", "categories", "users",
    ]:
        op.drop_table(tbl)

    for enum_name in [
        "currency", "userrole", "orderstatus", "transactionstatus",
        "paymentmethod", "purchaseorderstatus", "movementtype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")